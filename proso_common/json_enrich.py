import logging
from time import time
from django.core.cache import cache
import json as json_lib
from django.core.urlresolvers import reverse
from proso.django.response import pass_get_parameters_string, append_get_parameters
from proso_models.models import get_environment


LOGGER = logging.getLogger('django.request')
CACHE_EXPIRATION = 60 * 60 * 24 * 30


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


def enrich_by_predicate(request, json, fun, predicate, skip_nested=False, **kwargs):
    time_start = time()
    collected = []
    memory = {'nested': False}

    def _collect(json_inner, nested):
        if nested and skip_nested:
            return
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
        fun(request, collected, memory['nested'], **kwargs)
    LOGGER.debug("enrichment of JSON by predicate by '%s' function took %s seconds", fun.__name__, (time() - time_start))
    return json


def enrich_by_object_type(request, json, fun, object_type, skip_nested=False, **kwargs):
    if isinstance(object_type, list):
        f = lambda x: 'object_type' in x and x['object_type'] in object_type
    else:
        f = lambda x: 'object_type' in x and x['object_type'] == object_type
    return enrich_by_predicate(request, json, fun, f, skip_nested=skip_nested, **kwargs)


def url(request, json_list, nested, url_name='show_{}', ignore_get=None):
    if not ignore_get:
        ignore_get = []
    urls = cache.get('proso_urls')
    if urls is None:
        urls = {}
    else:
        urls = json_lib.loads(urls)
    cache_updated = False
    pass_string = pass_get_parameters_string(request, ignore_get)
    for json in json_list:
        if 'object_type' not in json or 'id' not in json:
            continue
        key = 'show_%s_%s' % (json['object_type'], json['id'])
        if key in urls:
            json['url'] = urls[key]
        else:
            cache_updated = True
            json['url'] = reverse(url_name.format(json['object_type']), kwargs={'id': json['id']})
            urls[key] = json['url']
        json['url'] = append_get_parameters(json['url'], pass_string)
    if cache_updated:
        cache.set('proso_urls', json_lib.dumps(urls), CACHE_EXPIRATION)


def env_variables(request, json_list, nested, variable_type):
    environment = get_environment()
    items = [json["item_id"] for json in json_list]

    for json in json_list:
        if env_variables not in json:
            json["env_variables"] = {}

    for (key, user, relationship) in variable_type:
        if not relationship:
            for json, v in zip(json_list, environment.read_more_items(key, items, user)):
                if v:
                    json["env_variables"][key] = v
        else:
            for json, v in zip(json_list, environment.get_items_with_values_more_items(key, items, user)):
                json["env_variables"][key] = dict(v)
