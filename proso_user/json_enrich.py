from django.core.cache import cache
import json as json_lib
from proso_common.json_enrich import CACHE_EXPIRATION
from proso.django.response import pass_get_parameters_string, append_get_parameters
from django.core.urlresolvers import reverse
from proso.django.request import get_user_id
from .models import UserQuestionAnswer
from collections import defaultdict


IGNORE_GET = []


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


def user_answers(request, json_list, nested):
    if nested:
        return
    user_id = get_user_id(request)
    user_answers = defaultdict(list)
    for user_answer in UserQuestionAnswer.objects.select_related('question', 'closed_answer').filter(user_id=user_id):
        user_answers[user_answer.question.identifier].append(user_answer)
    for question in json_list:
        possible_answers = {ans['identifier']: ans for ans in question['possible_answers']}
        question_user_answers = [ans.to_json(nested=True) for ans in user_answers[question['identifier']]]
        for ans in question_user_answers:
            if 'closed_answer' in ans:
                ans['closed_answer'] = possible_answers[ans['closed_answer']['identifier']]
        question['user_answers'] = question_user_answers
