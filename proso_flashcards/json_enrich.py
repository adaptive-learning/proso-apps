from collections import defaultdict
from proso_flashcards.models import Flashcard


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
