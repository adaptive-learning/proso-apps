from collections import defaultdict
from proso_user.models import get_user_id
from proso.django.request import get_time
from proso_models.json_enrich import _environment
from proso_models.models import get_predictive_model
from proso_flashcards.models import Flashcard
from functools import reduce


def avg_prediction(request, json_list, nested):
    category_items = {json["id"]: Flashcard.objects.under_categories_as_items([json["id"]])
                      for json in json_list if json["object_type"] == "fc_category"}
    term_items = {json["id"]: Flashcard.objects.under_terms_as_items([json["id"]])
                  for json in json_list if json["object_type"] == "fc_term"}
    context_items = {json["id"]: Flashcard.objects.in_contexts_as_items([json["id"]])
                     for json in json_list if json["object_type"] == "fc_context"}
    all_items = list(set(reduce(lambda a, b: a + b,
                                list(category_items.values()) + list(term_items.values()) + list(context_items.values()))))
    user = get_user_id(request, allow_override=True)
    time = get_time(request)
    predictions = dict(list(zip(all_items, get_predictive_model().predict_more_items(
        _environment(request),
        user,
        all_items,
        time
    ))))

    for json in json_list:
        prediction = []
        if json["object_type"] == "fc_category":
            prediction = [predictions[item] for item in category_items[json["id"]]]
        if json["object_type"] == "fc_term":
            prediction = [predictions[item] for item in term_items[json["id"]]]
        if json["object_type"] == "fc_context":
            prediction = [predictions[item] for item in context_items[json["id"]]]
        p = None if len(prediction) == 0 else sum(prediction) / len(prediction)
        json["avg_prediction"] = p


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


def practiced(request, json_list, nested):
    flashcards_ids = [json["id"] for json in json_list if json["object_type"] == "fc_flashcard"]
    user = get_user_id(request, allow_override=True)
    counts = Flashcard.objects.number_of_answers_per_fc(flashcards_ids, user)
    for json in json_list:
        json["practiced"] = counts[json["id"]] > 0
