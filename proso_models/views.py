from django.http import HttpResponseBadRequest
from proso.django.request import is_time_overridden, get_time, get_user_id
from proso.django.response import render_json
from models import get_environment, get_active_environment_info, Item
import numpy
import json_enrich
import proso_common.json_enrich as common_json_enrich
from lazysignup.decorators import allow_lazy_user


@allow_lazy_user
def status(request):
    user_id = get_user_id(request)
    time = get_time(request)
    environment = get_environment()
    if is_time_overridden(request):
        environment.shift_time(time)
    return render_json(request, _to_json(request, {
        'object_type': 'status',
        'number_of_answers': environment.number_of_answers(user=user_id),
        'number_of_correct_answers': environment.number_of_correct_answers(user=user_id),
        'environment_info': get_active_environment_info(),
    }), template='models_json.html')


@allow_lazy_user
def model(request):
    if 'items' not in request.GET:
        return HttpResponseBadRequest('GET parameter "items" has to be specified')
    item_ids = list(set(map(int, request.GET['items'].split(','))))
    items = Item.objects.filter(id__in=item_ids).all()
    if len(items) != len(item_ids):
        found_item_ids = map(lambda item: item.id, items)
        not_found_item_ids = set(item_ids) - set(found_item_ids)
        return render_json(request, {
            'error': 'There are no items with the following ids: %s' % list(not_found_item_ids)
        }, template='models_json.html', status=404)
    result = {
        'object_type': 'model',
        'items': map(lambda item: item.to_json(), items)
    }
    return render_json(request, _to_json(request, result), template='models_json.html')


@allow_lazy_user
def audit(request, key):
    if 'user' in request.GET:
        user = get_user_id(request)
    else:
        user = None
    limit = 100
    if request.user.is_staff:
        limit = request.GET.get(limit, limit)
    item = int(request.GET['item']) if 'item' in request.GET else None
    item_secondary = int(request.GET['item_secondary']) if 'item_secondary' in request.GET else None
    time = get_time(request)
    environment = get_environment()
    if is_time_overridden(request):
        environment.shift_time(time)
    values = environment.audit(
        key, user=user, item=item, item_secondary=item_secondary, limit=limit)

    def _to_json_audit((time, value)):
        return _to_json(request, {
            'object_type': 'value',
            'key': key,
            'item_primary_id': item,
            'item_secondary_id': item_secondary,
            'user_id': user,
            'value': value,
            'time': time.strftime('%Y-%m-%d %H:%M:%S')
        })
    return render_json(request, map(_to_json_audit, values), template='models_json.html')


@allow_lazy_user
def read(request, key):
    if 'user' in request.GET:
        user = get_user_id(request)
    else:
        user = None
    item = int(request.GET['item']) if 'item' in request.GET else None
    item_secondary = int(request.GET['item_secondary']) if 'item_secondary' in request.GET else None
    time = get_time(request)
    environment = get_environment()
    if is_time_overridden(request):
        environment.shift_time(time)
    value = environment.read(key, user=user, item=item, item_secondary=item_secondary)
    if value is None:
        return render_json(
            request,
            {'error': 'value with key "%s" not found' % key},
            template='models_json.html', status=404)
    else:
        return render_json(
            request,
            _to_json(request, {
                'object_type': 'value',
                'key': key,
                'item_primary_id': item,
                'item_secondary_id': item_secondary,
                'user_id': user,
                'value': value
            }),
            template='models_json.html'
        )


def _to_json(request, value):
    json = value
    group_enricher = lambda key, aggr_fun: (lambda r, j, nested: json_enrich.group_item_keys(r, j, nested, key, aggr_fun))
    common_json_enrich.enrich_by_object_type(
        request, json, json_enrich.prediction, ['item'])
    common_json_enrich.enrich_by_object_type(
        request, json, json_enrich.number_of_answers, ['item'])
    common_json_enrich.enrich_by_object_type(
        request, json, json_enrich.number_of_correct_answers, ['item'])
    enrichers = [
        json_enrich.audit_url,
        group_enricher('prediction', numpy.mean),
        group_enricher('mastered', numpy.mean),
        group_enricher('number_of_answers', sum),
        group_enricher('covered', numpy.mean),
        group_enricher('number_of_correct_answers', sum),
        group_enricher('covered_correctly', numpy.mean)
    ]
    for enricher in enrichers:
        common_json_enrich.enrich(request, json, enricher)
    return json
