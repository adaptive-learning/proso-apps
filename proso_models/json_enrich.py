from proso.django.config import get_config
from proso.django.response import pass_get_parameters
from django.core.urlresolvers import reverse
from proso.django.request import is_time_overridden, get_time, get_user_id
import models
import numpy


def prediction(request, json_list, nested):
    object_item_ids = map(lambda x: x['item_id'], json_list)
    user = get_user_id(request)
    time = get_time(request)
    predictions = _predictive_model().predict_more_items(_environment(request), user, object_item_ids, time)
    mastery_threshold = get_config("proso_models", "mastery_threshold", default=0.9)
    for object_json, prediction in zip(json_list, predictions):
        object_json['prediction'] = float("{0:.2f}".format(prediction))
        object_json['mastered'] = prediction >= mastery_threshold
    if "new_user_predictions" in request.GET:
        user = -1
        predictions = _predictive_model().predict_more_items(_environment(request), user, object_item_ids, time)
        for object_json, prediction in zip(json_list, predictions):
            object_json['new_user_prediction'] = float("{0:.2f}".format(prediction))
    return json_list


def number_of_answers(request, json_list, nested):
    object_item_ids = map(lambda x: x['item_id'], json_list)
    user = get_user_id(request)
    number_of_answers = _environment(request).number_of_answers_more_items(
        user=user, items=object_item_ids)
    for object_json, num in zip(json_list, number_of_answers):
        object_json['number_of_answers'] = num
        object_json['covered'] = num > 0
    return json_list


def number_of_correct_answers(request, json_list, nested):
    object_item_ids = map(lambda x: x['item_id'], json_list)
    user = get_user_id(request)
    number_of_correct_answers = _environment(request).number_of_correct_answers_more_items(
        user=user, items=object_item_ids)
    for object_json, num in zip(json_list, number_of_correct_answers):
        object_json['number_of_correct_answers'] = num
        object_json['covered_correctly'] = num > 0
    return json_list


def group_item_keys(request, json, nested, key, aggr_fun=numpy.mean):
    if 'items' not in json:
        return json
    collected = map(lambda item: item[key], json['items'])
    aggregated = aggr_fun(collected)
    if isinstance(aggregated, int):
        show = aggregated
    else:
        show = float("{0:.2f}".format(aggr_fun(collected)))
    json['group_' + key] = show
    return json


def audit_url(request, json, nested):
    if 'object_type' not in json or json['object_type'] != 'value':
        return json
    url = reverse('audit', kwargs={'key': json['key']})
    url_suffix = ''
    if json['user_id']:
        url_suffix += '&user=%s' % json['user_id']
    if json['item_primary_id']:
        url_suffix += '&item=%s' % json['item_primary_id']
    if json['item_secondary_id']:
        url_suffix += '&item_secondary=%s' % json['item_secondary_id']
    if url_suffix:
        url += '?' + url_suffix[1:]
    json['audit_url'] = pass_get_parameters(request, url, ignore=['item', 'item_secondary', 'user'])
    return json


def _environment(request):
    environment = models.get_environment()
    if is_time_overridden(request):
        time = get_time(request)
        environment.shift_time(time)
    return environment


def _predictive_model():
    return models.get_predictive_model()
