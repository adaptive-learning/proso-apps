import logging
from django.core.cache import cache
import json as json_lib
from django.core.urlresolvers import reverse
from proso.django.response import pass_get_parameters_string, append_get_parameters
from proso_models.models import get_environment


LOGGER = logging.getLogger('django.request')
CACHE_EXPIRATION = 60 * 60 * 24 * 30


def url(request, json_list, nested, url_name='show_{}', ignore_get=None):
    """
    Enrich the given list of objects, so they have URL.

    Args:
        request (django.http.request.HttpRequest): request which is currently processed
        json_list (list): list of dicts (JSON objects to be enriched)
        url_name (str|fun): pattern to create a url name taking object_type
        ignore_get (list): list of GET parameters which are ignored when the URL is generated

    Returns:
        list: list of dicts (enriched JSON objects)
    """
    if not ignore_get:
        ignore_get = []
    if isinstance(url_name, str):
        url_string = str(url_name)
        url_name = lambda x: url_string.format(x)
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
            json['url'] = reverse(url_name(json['object_type']), kwargs={'id': json['id']})
            urls[key] = json['url']
        json['url'] = append_get_parameters(json['url'], pass_string)
    if cache_updated:
        cache.set('proso_urls', json_lib.dumps(urls), CACHE_EXPIRATION)


def env_variables(request, json_list, nested, variable_type):
    if 'environment' not in request.GET:
        return
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
