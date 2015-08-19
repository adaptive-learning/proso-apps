from django.http import HttpResponseBadRequest
from proso.django.request import is_time_overridden, get_time, get_user_id, load_query_json
from proso.django.response import render_json
from models import get_environment, get_active_environment_info, Item, recommend_users as models_recommend_users, PracticeContext, learning_curve as models_learning_curve
import datetime
import numpy
import json_enrich
import proso_common.json_enrich as common_json_enrich
from lazysignup.decorators import allow_lazy_user
from django.contrib.admin.views.decorators import staff_member_required


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


@staff_member_required
def learning_curve(request):
    '''
    Shows a learning curve based on the randomized testing.

    GET parameters:
      length:
        length of the learning curve
      context:
        JSON representing the practice context
      all_users:
        if present stop filtering users based on the minimal number of testing
        answers (=length)
    '''
    context = PracticeContext.objects.from_content(load_query_json(request.GET, 'context', '{}'))
    length = int(request.GET.get('length', 10))
    if 'all_users' in request.GET:
        user_length = 1
    else:
        user_length = None
    return render_json(
        request, _to_json(
            request, models_learning_curve(length,
            context=context.id, user_length=user_length)
        ),
        template='models_json.html', help_text=learning_curve.__doc__)


@staff_member_required
def recommend_users(request):
    '''
    Recommend users for further analysis.

    GET parameters:
      register_min:
        minimal date of user's registration ('%Y-%m-%d')
      register_max:
        maximal date of user's registration ('%Y-%m-%d')
      number_of_answers_min:
        minimal number of user's answers
      number_of_answers_max:
        maximal number of user's answers
      success_min:
        minimal user's success rate
      success_max:
        maximal user's success rate
      variable_name:
        name of the filtered parameter
      variable_min:
        minimal value of the parameter of the model
      variable_max:
        maximal value of parameter of the model
      limit:
        number of returned questions (default 10, maximum 100)
    '''
    limit = int(request.GET.get('limit', 1))

    def _get_interval(key):
        return request.GET.get('{}_min'.format(key)), request.GET.get('{}_max'.format(key))

    def _convert_time_interval(interval):
        mapped = map(lambda x: None if x is None else datetime.datetime.strptime(x, '%Y-%m-%d'), list(interval))
        return mapped[0], mapped[1]

    recommended = models_recommend_users(
        _convert_time_interval(_get_interval('register')),
        _get_interval('number_of_answers'),
        _get_interval('success'),
        request.GET.get('variable_name'),
        _get_interval('variable'),
        limit)
    return render_json(request, recommended, template='models_json.html', help_text=recommend_users.__doc__)


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
        limit = request.GET.get('limit', limit)
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
