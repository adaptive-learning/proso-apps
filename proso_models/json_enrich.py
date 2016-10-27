from proso_models.models import get_mastery_trashold
from . import models
from proso.django.request import is_time_overridden, get_time, get_user_id, get_language
from proso.list import flatten, group_by
import numpy


def item2object(request, json_list, nested):
    if any([x.get('object_type', '') != 'item' for x in json_list]):
        raise Exception('Only items can be translated to objects!')
    item_ids = [x['id'] for x in json_list]
    translated = models.Item.objects.translate_item_ids(item_ids, get_language(request), is_nested=nested)
    for object_json in json_list:
        for key, value in translated[object_json['id']].items():
            object_json[key] = value


def prediction(request, json_list, nested):
    if 'stats' not in request.GET:
        return
    object_item_ids = [x['item_id'] for x in json_list]
    user = get_user_id(request)
    time = models.get_time_for_knowledge_overview(request)
    predictions = _predictive_model().predict_more_items(_environment(request), user, object_item_ids, time)
    mastery_threshold = get_mastery_trashold()
    for object_json, prediction in zip(json_list, predictions):
        object_json['prediction'] = float("{0:.2f}".format(prediction))
        object_json['mastered'] = prediction >= mastery_threshold
    if "new_user_predictions" in request.GET:
        user = -1
        predictions = _predictive_model().predict_more_items(_environment(request), user, object_item_ids, time)
        for object_json, prediction in zip(json_list, predictions):
            object_json['new_user_prediction'] = float("{0:.2f}".format(prediction))
    return json_list


def avg_prediction(request, json_list, nested):
    if 'stats' not in request.GET:
        return
    object_item_ids = [x['item_id'] for x in json_list]
    leaves = models.Item.objects.get_leaves(object_item_ids, language=get_language(request))
    all_leaves = list(set(flatten(leaves.values())))
    user = get_user_id(request)
    time = models.get_time_for_knowledge_overview(request)
    predictions = dict(list(zip(all_leaves, _predictive_model().predict_more_items(
        _environment(request),
        user,
        all_leaves,
        time
    ))))
    mastery_threshold = get_mastery_trashold()
    for object_json in json_list:
        leaf_predictions = [predictions[leave] for leave in leaves[object_json['item_id']]]
        object_json['avg_predicton'] = numpy.mean(leaf_predictions)
        object_json['mastered'] = sum([p > mastery_threshold for p in leaf_predictions])


def number_of_answers(request, json_list, nested):
    if 'stats' not in request.GET:
        return
    object_item_ids = [x['item_id'] for x in json_list]
    user = get_user_id(request)

    leaves = models.Item.objects.get_leaves(object_item_ids, language=get_language(request))
    all_leaves = list(set(flatten(leaves.values())))
    number_of_answers = _environment(request).number_of_answers_more_items(
        user=user, items=all_leaves)
    for object_json in json_list:
        num = sum([number_of_answers[leave] for leave in leaves[object_json['item_id']]])
        object_json['number_of_answers'] = num
        object_json['practiced'] = num > 0
    return json_list


def number_of_correct_answers(request, json_list, nested):
    if 'stats' not in request.GET:
        return
    object_item_ids = [x['item_id'] for x in json_list]
    user = get_user_id(request)
    leaves = models.Item.objects.get_leaves(object_item_ids, language=get_language(request))
    all_leaves = set(flatten(leaves.values()))
    number_of_correct_answers = _environment(request).number_of_correct_answers_more_items(
        user=user, items=all_leaves)
    for object_json in json_list:
        num = sum([number_of_correct_answers[leave] for leave in leaves[object_json['item_id']]])
        object_json['number_of_correct_answers'] = num
        object_json['practiced_correctly'] = num > 0
    return json_list


def answers_in_practice_set(request, json_list, nested):
    set_ids = [s['id'] for s in json_list]
    answers = group_by(models.Answer.objects.answers(models.Answer.objects.filter(practice_set__in=set_ids).values_list('id', flat=True)), by=lambda a: a.practice_set.id)
    for practice_set in json_list:
        practice_set['answers'] = sorted([a.to_json() for a in answers.get(practice_set['id'], [])], key=lambda a: a['id'])


def _environment(request):
    environment = models.get_environment()
    if is_time_overridden(request):
        time = get_time(request)
        environment.shift_time(time)
    return environment


def _predictive_model():
    return models.get_predictive_model()
