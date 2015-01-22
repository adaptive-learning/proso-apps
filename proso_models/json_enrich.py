from proso.django.response import pass_get_parameters
from django.core.urlresolvers import reverse
from proso.django.request import is_time_overriden, get_time, get_user_id
import models


def prediction(request, json_list, nested):
    object_item_ids = map(lambda x: x['item_id'], json_list)
    user = get_user_id(request)
    time = get_time(request)
    predictions = _predictive_model().predict_more_items(
        _environment(request),
        user,
        object_item_ids,
        time)
    for object_json, prediction in zip(json_list, predictions):
        object_json['prediction'] = float("{0:.2f}".format(prediction))
    return json_list


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
    if is_time_overriden(request):
        time = get_time(request)
        environment.shift_time(time)
    return environment


def _predictive_model():
    return models.get_predictive_model()
