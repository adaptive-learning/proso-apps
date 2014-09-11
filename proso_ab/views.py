from django.shortcuts import render
from proso.django.response import render_json


def home(request):
    return render(request, 'ab_home.html', {})


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
    json = map(lambda x: x.to_json(), objs)
    return render_json(request, json, template='ab_json.html')
