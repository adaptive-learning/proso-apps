import logging
from time import time


LOGGER = logging.getLogger('django.request')


def enrich(request, json, fun, nested=False, top_level=True):
    time_start = time()
    if isinstance(json, list):
        result = map(lambda x: enrich(request, x, fun, top_level=False), json)
    elif isinstance(json, dict):
        json = fun(request, json, nested=nested)
        result = {k: enrich(request, v, fun, nested=True, top_level=False) for k, v in json.items()}
    else:
        result = json
    if top_level:
        LOGGER.debug("enrichment of JSON by '%s' function took %s seconds", fun.__name__, (time() - time_start))
    return result


def enrich_by_predicate(request, json, fun, predicate):
    time_start = time()
    collected = []
    memory = {'nested': False}

    def _collect(json_inner, nested):
        if isinstance(json_inner, list):
            map(lambda x: _collect(x, nested), json_inner)
        elif isinstance(json_inner, dict):
            if predicate(json_inner):
                collected.append(json_inner)
                if nested:
                    memory['nested'] = True
            map(lambda x: _collect(x, True), json_inner.values())
    _collect(json, False)
    if len(collected) > 0:
        fun(request, collected, memory['nested'])
    LOGGER.debug("enrichment of JSON by predicate by '%s' function took %s seconds", fun.__name__, (time() - time_start))
    return json


def enrich_by_object_type(request, json, fun, object_type):
    if isinstance(object_type, list):
        f = lambda x: 'object_type' in x and x['object_type'] in object_type
    else:
        f = lambda x: 'object_type' in x and x['object_type'] == object_type
    return enrich_by_predicate(request, json, fun, f)
