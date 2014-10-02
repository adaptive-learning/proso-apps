from django.shortcuts import render
from proso.django.response import render_json
import json_enrich
import proso_common.json_enrich as common_json_enrich
from django.shortcuts import get_object_or_404
from models import Experiment
from lazysignup.decorators import allow_lazy_user


def home(request):
    return render(request, 'ab_home.html', {})


def show_one(request, object_class, id):
    obj = get_object_or_404(object_class, pk=id)
    json = _to_json(request, obj)
    return render_json(request, json, template='ab_json.html')


def show_more(request, object_class):
    related = {}
    select_related = related.get(object_class, [])
    if 'filter_column' in request.GET and 'filter_value' in request.GET:
        column = request.GET['filter_column']
        value = request.GET['filter_value']
        if value.isdigit():
            value = int(value)
        objs = object_class.objects.select_related(*select_related).filter(
            **{column: value})
    else:
        objs = object_class.objects.select_related(*select_related).all()
    json = _to_json(request, list(objs))
    return render_json(request, json, template='ab_json.html')


@allow_lazy_user
def profile(request):
    objs = Experiment.objects.get_values(request)
    json = _to_json(request, objs)
    return render_json(request, json, template='ab_json.html')


def _to_json(request, value):
    if isinstance(value, list):
        json = map(lambda x: x if isinstance(x, dict) else x.to_json(), value)
    else:
        if isinstance(value, dict):
            json = value
        else:
            json = value.to_json()
    common_json_enrich.enrich_by_object_type(request, json, json_enrich.values, 'experiment')
    for enricher in [json_enrich.url]:
        json = common_json_enrich.enrich(request, json, enricher)
    return json
