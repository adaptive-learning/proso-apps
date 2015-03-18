import logging
from proso.django.cache import cache_page_conditional
import proso_common.views
from time import time as time_lib
import json_enrich
import proso_common.json_enrich as common_json_enrich

LOGGER = logging.getLogger('django.request')

@cache_page_conditional(condition=lambda request: 'stats' not in request.GET)
def show_one(request, object_class, id):
    return proso_common.views.show_one(
        request, _to_json, object_class, id, template='flashcards_json.html')


@cache_page_conditional(
    condition=lambda request: 'stats' not in request.GET)
def show_more(request, object_class, should_cache=True):
    def _load_objects(request, object_class):
        select_related_all = {
        }
        prefetch_related_all = {
        }
        select_related = select_related_all.get(object_class, [])
        prefetch_related = prefetch_related_all.get(object_class, [])
        if 'filter_column' in request.GET and 'filter_value' in request.GET:
            column = request.GET['filter_column']
            value = request.GET['filter_value']
            if value.isdigit():
                value = int(value)
            objs = (object_class.objects.
                    select_related(*select_related).
                    prefetch_related(*prefetch_related).filter(**{column: value}))
        else:
            objs = object_class.objects.select_related(*select_related). \
                prefetch_related(*prefetch_related).all()
        return objs

    return proso_common.views.show_more(
        request, _to_json, _load_objects, object_class,
        should_cache=should_cache, template='flashcards_json.html')


def _to_json(request, value):
    time_start = time_lib()
    if isinstance(value, list):
        json = map(lambda x: x if isinstance(x, dict) else x.to_json(), value)
    elif not isinstance(value, dict):
        json = value.to_json()
    else:
        json = value
    LOGGER.debug("converting value to simple JSON took %s seconds", (time_lib() - time_start))
    common_json_enrich.enrich_by_predicate(request, json, json_enrich.url, lambda x: True)
    LOGGER.debug("converting value to JSON took %s seconds", (time_lib() - time_start))
    return json
