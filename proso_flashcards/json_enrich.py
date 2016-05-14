from .flashcard_construction import get_direction, get_option_set
from proso_models.models import Item, get_item_selector, get_option_selector, get_environment
from collections import defaultdict
from proso_flashcards.models import Flashcard, FlashcardAnswer
from proso_models.json_enrich import item2object
from proso_user.models import get_user_id
from proso.django.request import get_time, is_time_overridden


def answer_type(request, json_list, nested):
    for question in json_list:
        if question['payload']['object_type'] == 'fc_flashcard':
            question['answer_class'] = 'flashcard_answer'


def options(request, json_list, nested):
    environment = get_environment()
    user_id = get_user_id(request)
    time = get_time(request)
    if is_time_overridden(request):
        environment.shift_time(time)
    item_selector = get_item_selector()
    option_selector = get_option_selector(item_selector)
    option_sets = get_option_set().get_option_for_flashcards([
        question['payload']
        for question in json_list
        if question['payload']['object_type'] == 'fc_flashcard'
    ])
    metas = [question.get('meta', {}) for question in json_list]
    test_position = _test_index(metas)
    selected_items = [question['payload']['item_id'] for question in json_list]
    allow_zero_option = {}
    for question in json_list:
        if question['payload']['object_type'] != 'fc_flashcard':
            continue
        if len(option_sets[question['payload']['item_id']]) == 0:
            # If we do not have enough options, we have to force direction
            question['question_type'] = FlashcardAnswer.FROM_TERM
        allow_zero_option[question['payload']['item_id']] = question['question_type'] == FlashcardAnswer.FROM_TERM

    is_flashcard_question = [question['payload']['object_type'] == 'fc_flashcard' for question in json_list]
    if not all(is_flashcard_question):
        # TODO: We should support mixed questions in the future
        raise Exception('All questions must be for flashcards!')

    all_options = option_selector.select_options_more_items(
        environment, user_id, selected_items, time, option_sets,
        allow_zero_options=allow_zero_option
    )
    options_json_list = []
    for i, (question, options) in enumerate(zip(json_list, all_options)):
        if test_position is not None and test_position == i:
            question['question_type'] = FlashcardAnswer.FROM_TERM
            question['payload']['options'] = []
            continue
        question['payload']['options'] = [Item.objects.item_id_to_json(o) for o in options]
        options_json_list += question['payload']['options']
    item2object(request, options_json_list, nested=False)


def question_type(request, json_list, nested):
    direction = get_direction()
    for question in json_list:
        if question['payload']['object_type'] == 'fc_flashcard':
            question['question_type'] = direction.get_direction(question['payload'])


def answer_flashcards(request, json_list, nested):
    asked_item_ids = [a['item_asked_id'] for a in json_list]
    answered_item_ids = [a.get('item_answered_id', None) for a in json_list]
    flashcard_item_ids = asked_item_ids + [x for x in answered_item_ids if x is not None]
    if len(flashcard_item_ids) == 0:
        return

    flashcards = defaultdict(dict)
    for f in Flashcard.objects.filter(item_id__in=flashcard_item_ids).select_related(Flashcard.related_term()):
        flashcards[f.item_id][f.lang] = f

    for answer in json_list:
        if 'lang' in answer:
            answer_lang = answer['lang']
        elif 'options' in answer and len(answer['options']) > 0:
            answer_lang = answer['options'][0]['lang']
        else:
            answer_lang = list(flashcards[answer['item_asked_id']].keys())[0]
        answer['flashcard_asked'] = flashcards[answer['item_asked_id']][answer_lang].to_json(nested=True)
        if answer['item_answered_id']:
            answer['flashcard_answered'] = flashcards[answer['item_answered_id']][answer_lang].to_json(nested=True)


def _test_index(meta):
    check = [m is not None and 'without_options' in m.get('test', '') for m in meta]
    return check.index(True) if any(check) else None
