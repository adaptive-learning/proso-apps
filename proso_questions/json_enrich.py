from models import Image, Option, Question
from django.core.urlresolvers import reverse
import markdown
import numpy
from proso.django.request import get_time, get_user_id
import proso_models.models


def enrich(request, json, fun, nested=False):
    if isinstance(json, list):
        return map(lambda x: enrich(request, x, fun), json)
    elif isinstance(json, dict):
        json = fun(request, json, nested=nested)
        return {k: enrich(request, v, fun, nested=True) for k, v in json.items()}
    else:
        return json


def enrich_by_predicate(request, json, fun, predicate):
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
    return json


def enrich_by_object_type(request, json, fun, object_type):
    return enrich_by_predicate(
        request, json, fun,
        lambda x: 'object_type' in x and x['object_type'] == object_type
    )


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
    ignored_get = ['filter_column', 'filter_value']
    url_options = '?filter_column={}&filter_value=' + str(json['id'])
    url = reverse('show_questions') + url_options
    if json['object_type'] == 'set':
        json['questions_url'] = _pass_get_parameters(
            request, url.format('question_set_id'), ignored_get)
    elif json['object_type'] == 'category':
        json['questions_url'] = _pass_get_parameters(
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


def images(request, json_list, nested):
    object_type = json_list[0]['object_type']
    object_ids = map(lambda x: x['id'], json_list)
    images = Image.objects.filter(
        **{'%s_id__in' % object_type: object_ids})
    images_dict = {}
    for img in images:
        object_id = getattr(img, '%s_id' % object_type)
        found = images_dict.get(object_id, [])
        found.append(img.to_json())
        images_dict[object_id] = found
    for json in json_list:
        json['images'] = images_dict.get(json['id'], [])
    return json_list


def options(request, json_list, nested):
    object_ids = map(lambda x: x['id'], json_list)
    options = Option.objects.filter(question_id__in=object_ids)
    options_dict = {}
    for opt in options:
        object_id = opt.question_id
        found = options_dict.get(object_id, [])
        found.append(opt.to_json(nested=True))
        options_dict[object_id] = found
    for json in json_list:
        json['options'] = options_dict.get(json['id'], [])
    return json_list


def url(request, json, nested):
    if 'object_type' in json and 'id' in json:
        json['url'] = _pass_get_parameters(
            request,
            reverse('show_' + json['object_type'], kwargs={'id': json['id']}),
            ['filter_column', 'filter_value']
        )
    return json


def prediction(request, json_list, nested):
    object_type = json_list[0]['object_type']
    if object_type == 'question':
        return prediction_question(request, json_list, nested)
    else:
        return prediction_group(request, json_list, nested)


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
    if nested:
        return False
    object_ids = map(lambda x: x['id'], json_list)
    object_type = json_list[0]['object_type']
    if object_type not in ['category', 'set']:
        raise Exception('object type "%s" is not supported' % object_type)
    if object_type == 'set':
        object_type = 'question_set'
    questions = Question.objects.filter(**{'%s_id__in' % object_type: object_ids})
    questions_dict = {}
    for q in questions:
        object_id = getattr(q, '%s_id' % object_type)
        found = questions_dict.get(object_id, [])
        found.append(q)
        questions_dict[object_id] = found
    question_item_ids = map(lambda x: x.item_id, questions)
    user = get_user_id(request)
    time = get_time(request)
    predictions = _predictive_model().predict_more_items(
        _environment(request),
        user,
        question_item_ids,
        time)
    predictions_dict = dict(zip(map(lambda x: x.id, questions), predictions))
    for obj in json_list:
        obj_qs = questions_dict.get(obj['id'], [])
        obj['prediction'] = float("{0:.2f}".format(numpy.mean(map(lambda q: predictions_dict[q.id], obj_qs))))


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


def _pass_get_parameters(request, dest_url, ignore=None):
    ignore = [] if ignore is None else ignore
    to_pass = filter(lambda x: x not in ignore, request.GET.keys())
    url_params = '&'.join(map(lambda x: '{}={}'.format(x, str(request.GET[x])), to_pass))
    prefix = '&' if dest_url.find('?') != -1 else '?'
    return dest_url + prefix + url_params


def _environment(request):
    environment = proso_models.models.get_environment()
    if 'time' in request.GET and request.user.is_staff:
        time = get_time(request)
        environment.shift_time(time)
    return environment


def _predictive_model():
    return proso_models.models.get_predictive_model()
