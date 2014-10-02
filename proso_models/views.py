from django.shortcuts import render
from django.http import HttpResponseBadRequest
from proso.django.request import get_time, get_user_id
from proso.django.response import render_json
from models import get_environment, get_predictive_model
import numpy


def home(request):
    return render(request, 'models_home.html', {})


def model(request):
    if 'items' not in request.GET:
        return HttpResponseBadRequest('GET parameter "items" has to be specified')
    user = get_user_id(request)
    time = get_time(request)
    environment = get_environment()
    predictive_model = get_predictive_model()
    if request.user.is_staff and 'time' in request.GET:
        environment.shift_time(time)
    items = map(int, request.GET['items'].split(','))
    preds = predictive_model.predict_more_items(environment, user, items, time)
    result = {}
    result['object_type'] = 'model'
    result['predictions'] = map(
        lambda (i, p): {'item_id': i, 'prediction': "{0:.2f}".format(p)},
        zip(items, preds))
    result['group_prediction'] = "{0:.2f}".format(numpy.mean(preds))
    return render_json(request, result, template='models_json.html')


def audit(request, key):
    limit = 100
    if request.user.is_staff:
        limit = request.GET.get(limit, limit)
    user = get_user_id(request)
    item = int(request.GET['item']) if 'item' in request.GET else None
    item_secondary = int(request.GET['item_secondary']) if 'item_secondary' in request.GET else None
    time = get_time(request)
    environment = get_environment()
    if request.user.is_staff and 'time' in request.GET:
        environment.shift_time(time)
    values = environment.audit(
        key, user=user, item=item, item_secondary=item_secondary, limit=limit)

    def _to_json((time, value)):
        return {
            'object_type': value,
            'key': key,
            'item_primary_id': item,
            'item_secondary_id': item_secondary,
            'user_id': user,
            'value': value,
            'time': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    return render_json(request, map(_to_json, values), template='models_json.html')


def read(request, key):
    user = get_user_id(request)
    item = int(request.GET['item']) if 'item' in request.GET else None
    item_secondary = int(request.GET['item_secondary']) if 'item_secondary' in request.GET else None
    time = get_time(request)
    environment = get_environment()
    if request.user.is_staff and 'time' in request.GET:
        environment.shift_time(time)
    value = environment.read(key, user=user, item=item, item_secondary=item_secondary)
    if value is None:
        return render_json(request, {'error': 'value not found'}, template='models_json.html', status=404)
    else:
        return render_json(
            request,
            {
                'object_type': 'value',
                'key': key,
                'item_primary_id': item,
                'item_secondary_id': item_secondary,
                'user_id': user,
                'value': value
            },
            template='models_json.html'
        )
