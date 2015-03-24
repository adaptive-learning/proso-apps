from models import Question
from django.core.urlresolvers import reverse
import markdown
from proso.django.response import pass_get_parameters_string, append_get_parameters, pass_get_parameters
from django.core.cache import cache
import json as json_lib
from proso_common.json_enrich import CACHE_EXPIRATION


IGNORE_GET = ['category']


def question(request, json_list, nested):
    if nested:
        return False
    object_type = json_list[0]['object_type']
    if object_type != 'answer':
        raise Exception('object type "%s" is not supported' % object_type)
    question_item_ids = map(lambda x: x['question_item_id'], json_list)
    qs = dict(map(
        lambda q: (q.item_id, q.to_json(nested=True)),
        list(Question.objects.filter(**{'item_id__in': question_item_ids}))))
    for answer in json_list:
        answer['question'] = qs[answer['question_item_id']]


def questions(request, json_list, nested):
    show_questions_url = reverse('show_questions')
    for json in json_list:
        if nested or 'object_type' not in json:
            continue
        ignored_get = ['filter_column', 'filter_value'] + IGNORE_GET
        url_options = '?filter_column={}&filter_value=' + str(json['id'])
        url = show_questions_url + url_options
        if json['object_type'] == 'set':
            json['questions_url'] = pass_get_parameters(
                request, url.format('set_id'), ignored_get)
        elif json['object_type'] == 'category':
            json['questions_url'] = pass_get_parameters(
                request, url.format('category_id'), ignored_get)


def test_evaluate(request, json_list, nested):
    urls = cache.get('proso_urls')
    if urls is None:
        urls = {}
    else:
        urls = json_lib.loads(urls)
    cache_updated = False
    pass_string = pass_get_parameters_string(request, ['filter_column', 'filter_value', 'stats'] + IGNORE_GET)
    for json in json_list:
        if 'object_type' not in json or json['object_type'] != 'set':
            continue
        key = 'test_evaluate_%s' % json['id']
        if key in urls:
            json['test_evaluate_url'] = urls[key]
        else:
            cache_updated = True
            json['test_evaluate_url'] = reverse('test_evaluate', kwargs={'question_set_id': json['id']})
            urls[key] = json['test_evaluate_url']
        json['test_evaluate_url'] = append_get_parameters(json['test_evaluate_url'], pass_string)
    if cache_updated:
        cache.set('proso_urls', json_lib.dumps(urls), CACHE_EXPIRATION)


def html(request, json_list, nested):
    htmls = cache.get('proso_questions_html')
    if htmls is None:
        htmls = {}
    else:
        htmls = json_lib.loads(htmls)
    cache_updated = False
    for json in json_list:
        if 'text' not in json or 'item_id' not in json:
            continue
        if str(json['item_id']) in htmls:
            json['html'] = htmls[str(json['item_id'])]
        else:
            cache_updated = True
            new_html = markdown.markdown(json['text'])
            json['html'] = new_html
            htmls[json['item_id']] = new_html
        if 'html' in request.GET:
            json['html'] = json['html'].replace('<', '&lt').replace('>', '&gt')
        if 'images' in json:
            for image in json['images']:
                json['html'] = json['html'].replace(
                    'src="' + image['name'] + '"',
                    'src="' + image['url'] + '"'
                )
    if cache_updated:
        cache.set('proso_questions_html', json_lib.dumps(htmls), CACHE_EXPIRATION)


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
        key = 'show_%s_%s' % (json['object_type'], json['id'])
        if key in urls:
            json['url'] = urls[key]
        else:
            cache_updated = True
            json['url'] = reverse('show_' + json['object_type'], kwargs={'id': json['id']})
            urls[key] = json['url']
        json['url'] = append_get_parameters(json['url'], pass_string)
    if cache_updated:
        cache.set('proso_urls', json_lib.dumps(urls), CACHE_EXPIRATION)
