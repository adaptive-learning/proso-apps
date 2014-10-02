from models import Question, Set, Category
from django.core.urlresolvers import reverse
import markdown
from proso.django.request import get_time, get_user_id
from proso.django.response import pass_get_parameters
import proso_models.models
import numpy

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


def questions(request, json, nested):
    if nested or 'object_type' not in json:
        return json
    ignored_get = ['filter_column', 'filter_value'] + IGNORE_GET
    url_options = '?filter_column={}&filter_value=' + str(json['id'])
    url = reverse('show_questions') + url_options
    if json['object_type'] == 'set':
        json['questions_url'] = pass_get_parameters(
            request, url.format('set_id'), ignored_get)
    elif json['object_type'] == 'category':
        json['questions_url'] = pass_get_parameters(
            request, url.format('category_id'), ignored_get)
    return json


def html(request, json, nested):
    if 'text' in json:
        json['html'] = markdown.markdown(json['text'])
        if 'html' in request.GET:
            json['html'] = json['html'].replace('<', '&lt').replace('>', '&gt')
        if 'images' in json:
            for image in json['images']:
                json['html'] = json['html'].replace(
                    'src="' + image['name'] + '"',
                    'src="' + image['url'] + '"'
                )
    return json


def url(request, json, nested):
    if 'object_type' in json and 'id' in json:
        json['url'] = pass_get_parameters(
            request,
            reverse('show_' + json['object_type'], kwargs={'id': json['id']}),
            ['filter_column', 'filter_value'] + IGNORE_GET
        )
    return json


def prediction(request, json_list, nested):
    object_type = json_list[0]['object_type']
    if object_type == 'question':
        return prediction_question(request, json_list, nested)
    elif object_type in ['set', 'category']:
        return prediction_group(request, json_list, nested)
    else:
        return json_list


def prediction_question(request, json_list, nested):
    if nested:
        return False
    object_item_ids = map(lambda x: x['item_id'], json_list)
    object_type = json_list[0]['object_type']
    if object_type != 'question':
        raise Exception('object type "%s" is not supported' % object_type)
    user = get_user_id(request)
    time = get_time(request)
    predictions = _predictive_model().predict_more_items(
        _environment(request),
        user,
        object_item_ids,
        time)
    for question_json, prediction in zip(json_list, predictions):
        question_json['prediction'] = float("{0:.2f}".format(prediction))
    return json_list


def prediction_group(request, json_list, nested):
    objects = {'set': Set, 'category': Category}
    if json_list[0]['object_type'] not in objects:
        return json_list
    ids = map(lambda o: o['id'], json_list)
    objs = objects[json_list[0]['object_type']].objects.prefetch_related('questions').filter(id__in=ids)
    questions_dict = {}
    for obj in objs:
        questions_dict[obj.id] = map(lambda q: q.item_id, obj.questions.all())
    all_questions = list(set([j for js in questions_dict.values() for j in js]))
    user = get_user_id(request)
    time = get_time(request)
    predictions = dict(zip(all_questions, _predictive_model().predict_more_items(
        _environment(request),
        user,
        all_questions,
        time)))
    for json in json_list:
        obj_qs = questions_dict[json['id']]
        json['prediction'] = float("{0:.2f}".format(numpy.mean(map(lambda q: predictions[q], obj_qs))))
    return json_list


def number_of_answers(request, json_list, nested):
    if nested:
        return False
    object_type = json_list[0]['object_type']
    if object_type != 'question':
        raise Exception('object type "%s" is not supported' % object_type)
    user = get_user_id(request)
    object_item_ids = map(lambda x: x['item_id'], json_list)
    nums = dict(zip(object_item_ids, _environment(request).number_of_answers_more_items(user=user, items=object_item_ids)))
    for obj in json_list:
        obj['number_of_answers'] = nums[obj['item_id']]


def _environment(request):
    environment = proso_models.models.get_environment()
    if 'time' in request.GET and request.user.is_staff:
        time = get_time(request)
        environment.shift_time(time)
    return environment


def _predictive_model():
    return proso_models.models.get_predictive_model()
