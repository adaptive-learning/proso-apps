from .flashcard_construction import get_direction, get_option_set
from collections import defaultdict
from proso.django.request import get_time, is_time_overridden
from proso.list import flatten
from proso.models.context import selected_item_context
from proso_common.models import get_config
from proso_flashcards.models import Flashcard, FlashcardAnswer
from proso_models.json_enrich import item2object
from proso_models.models import Item, get_item_selector, get_option_selector, get_environment
from proso_user.models import get_user_id


def answer_type(request, json_list, nested):
    for question in json_list:
        if question['payload']['object_type'] == 'fc_flashcard':
            question['answer_class'] = 'flashcard_answer'


def context_flashcards(request, json_list, nested):
    if nested or len(json_list) > 1:
        return
    leave_items = Item.objects.get_leaves([c['item_id'] for c in json_list])
    translated = Item.objects.translate_item_ids(flatten(leave_items.values()), json_list[0]['lang'])
    for context in json_list:
        context['flashcards'] = [translated[i] for i in leave_items[context['item_id']]]


def options(request, json_list, nested):
    environment = get_environment()
    user_id = get_user_id(request)
    time = get_time(request)
    if is_time_overridden(request):
        environment.shift_time(time)
    item_selector = get_item_selector()
    option_selector = get_option_selector(item_selector)
    option_sets = get_option_set().get_option_for_flashcards([
        (question['payload'], question['question_type'])
        for question in json_list
        if question['payload']['object_type'] == 'fc_flashcard'
    ])
    metas = [question.get('meta', {}) for question in json_list]
    test_position = _test_index(metas)
    selected_items = [question['payload']['item_id'] for question in json_list
                      if question['payload']['object_type'] == 'fc_flashcard']
    allow_zero_option = {}
    for question in json_list:
        if question['payload']['object_type'] != 'fc_flashcard':
            continue
        if len(option_sets[question['payload']['item_id']]) == 0 and 'term_secondary' not in question['payload']:
            # If we do not have enough options, we have to force direction
            question['question_type'] = FlashcardAnswer.FROM_TERM
        allow_zero_option[question['payload']['item_id']] = question['question_type'] in {FlashcardAnswer.FROM_TERM, FlashcardAnswer.FROM_TERM_SECONDARY_TO_TERM}

    all_options = {i: options for i, options in zip(selected_items, option_selector.select_options_more_items(
        environment, user_id, selected_items, time, option_sets,
        allow_zero_options=allow_zero_option
    ))}
    options_json_list = []
    # HACK: Here, we have to take into account reference questions with zero
    # options. In case of zero options we have to force a question type if the
    # restriction for zero options is enabled.
    config_zero_options_restriction = get_config('proso_models', 'options_count.parameters.allow_zero_options_restriction', default=False)
    for i, question in enumerate(json_list):
        if question['payload']['object_type'] != 'fc_flashcard':
            continue
        if test_position is not None and test_position == i:
            if 'term_secondary' not in question['payload'] and config_zero_options_restriction:
                question['question_type'] = FlashcardAnswer.FROM_TERM
            question['payload']['options'] = []
            continue
        options = all_options[question['payload']['item_id']]
        question['payload']['options'] = [Item.objects.item_id_to_json(o) for o in options]
        options_json_list += question['payload']['options']
    item2object(request, options_json_list, nested=True)
    for question in json_list:
        if question['payload']['object_type'] != 'fc_flashcard':
            continue
        sort_key = 'term_secondary' if question['question_type'] == FlashcardAnswer.FROM_TERM_TO_TERM_SECONDARY else 'term'
        question['payload']['options'] = sorted(question['payload']['options'], key=lambda o: o[sort_key]['name'])


def question_type(request, json_list, nested):
    items = sorted([question['payload']['item_id'] for question in json_list if question['payload']['object_type'] == 'fc_flashcard'])
    for question in json_list:
        if question['payload']['object_type'] == 'fc_flashcard':
            with selected_item_context(question['payload']['item_id'], items):
                # We instantiate a direction for each question separately, so it can
                # be dependent on the question payload. On the other side, it could
                # be really slow in the case of a large number of questions.
                question['question_type'] = get_direction().get_direction(question['payload'])


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
