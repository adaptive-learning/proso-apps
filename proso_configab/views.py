import proso_common.views
from models import Experiment
from time import time as time_lib
import logging
import proso_common.json_enrich as common_json_enrich
import json_enrich as configab_json_enrich


LOGGER = logging.getLogger('django.request')


def show_one(request, object_class, id):
    return proso_common.views.show_one(
        request, _to_json, object_class, id, template='configab_json.html')


def show_more(request, object_class, should_cache=True):

    def _load_objects(request, object_class):
        select_related_all = {}
        prefetch_related_all = {
            Experiment: ['possiblevalue_set__variable', 'experimentsetup_set__values']
        }
        select_related = select_related_all.get(object_class, [])
        prefetch_related = prefetch_related_all.get(object_class, [])
        objs = object_class.objects
        if len(select_related) > 0:
            objs = objs.select_related(*select_related)
        if 'filter_column' in request.GET and 'filter_value' in request.GET:
            column = request.GET['filter_column']
            value = request.GET['filter_value']
            if value.isdigit():
                value = int(value)

            objs = objs.prefetch_related(*prefetch_related).filter(**{column: value})
        else:
            objs = objs.prefetch_related(*prefetch_related).all()
        return objs

    return proso_common.views.show_more(
        request, _to_json, _load_objects, object_class,
        should_cache=should_cache, template='configab_json.html', to_json_kwargs={})


def _to_json(request, value):
    time_start = time_lib()
    if isinstance(value, list):
        json = map(lambda x: x if isinstance(x, dict) else x.to_json(), value)
    elif not isinstance(value, dict):
        json = value.to_json()
    else:
        json = value
    LOGGER.debug("converting value to simple JSON took %s seconds", (time_lib() - time_start))
    common_json_enrich.enrich_by_predicate(request, json, common_json_enrich.url, lambda x: True)
    if 'stats' in request.GET:
        common_json_enrich.enrich_by_object_type(
            request, json, configab_json_enrich.experiment_setup_stats, ['configab_experiment_setup'], skip_nested=False)

    LOGGER.debug("converting value to JSON took %s seconds", (time_lib() - time_start))
    return json
