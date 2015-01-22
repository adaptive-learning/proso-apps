from django.core.cache import cache
from proso.django.response import pass_get_parameters_string, append_get_parameters, pass_get_parameters
from django.core.urlresolvers import reverse
import json as json_lib


IGNORE_GET = ['category']
CACHE_EXPIRATION = 60 * 60 * 24 * 30

def flashcards(request, json_list, nested):
    show_flashcards_url = reverse('proso_flashcards_show_flashcards')
    for json in json_list:
        if nested or 'object_type' not in json:
            continue
        ignored_get = ['filter_column', 'filter_value'] + IGNORE_GET
        url_options = '?filter_column={}&filter_value=' + str(json['id'])
        url = show_flashcards_url + url_options
        if json['object_type'] == 'category':
            json['flashcards_url'] = pass_get_parameters(
                request, url.format('category_id'), ignored_get)


def url(request, json_list, nested):
    urls = cache.get('proso_urls')
    if urls is None:
        urls = {}
    else:
        urls = json_lib.loads(urls)
    cache_updated = False
    pass_string = pass_get_parameters_string(request, ['filter_column', 'filter_value'] + IGNORE_GET)
    for json in json_list:
        if 'object_type' not in json or 'id' not in json:
            continue
        key = 'proso_flashcards_show_%s_%s' % (json['object_type'], json['id'])
        if key in urls:
            json['url'] = urls[key]
        else:
            cache_updated = True
            json['url'] = reverse(
                'proso_flashcards_show_' + json['object_type'], kwargs={'id': json['id']})
            urls[key] = json['url']
        json['url'] = append_get_parameters(json['url'], pass_string)
    if cache_updated:
        cache.set('proso_urls', json_lib.dumps(urls), CACHE_EXPIRATION)
