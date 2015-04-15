from proso.django.request import get_user_id, get_time
from proso_models.json_enrich import _environment
from proso_models.models import get_predictive_model
from proso_flashcards.models import Flashcard


def avg_prediction(request, json_list, nested):
    category_items = {json["id"]: Flashcard.objects.under_categories_as_items([json["id"]])
             for json in json_list if json["object_type"] == "fc_category"}
    all_items = list(set(reduce(lambda a, b: a + b, category_items.values())))
    user = get_user_id(request)
    time = get_time(request)
    predictions = dict(zip(all_items, get_predictive_model().predict_more_items(
        _environment(request),
        user,
        all_items,
        time
    )))

    for json in json_list:
        category_prediction = [predictions[item] for item in category_items[json["id"]]]
        p = None if len(category_prediction) == 0 else sum(category_prediction) / len(category_prediction)
        json["avg_prediction"] = p
