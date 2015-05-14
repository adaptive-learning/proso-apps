from django.shortcuts import get_object_or_404
from models import Question, Option, DecoratedAnswer, Set, Category, get_test_evaluator
from proso_models.models import Answer
from proso.django.response import render, render_json, redirect_pass_get
from django.views.decorators.csrf import ensure_csrf_cookie
from lazysignup.decorators import allow_lazy_user
from django.http import HttpResponse, HttpResponseBadRequest
from django.db import transaction
import json_enrich
import proso_common.json_enrich as common_json_enrich
import proso_models.json_enrich as models_json_enrich
from proso.django.request import is_time_overridden, get_time, get_user_id
from proso_models.models import get_environment, get_item_selector
import logging
from time import time as time_lib
from proso.django.cache import cache_page_conditional
import proso_common.views


LOGGER = logging.getLogger('django.request')


@cache_page_conditional(condition=lambda request: 'stats' not in request.GET)
def show_one(request, object_class, id):
    return proso_common.views.show_one(
        request, _to_json, object_class, id, template='questions_json.html')


@cache_page_conditional(
    condition=lambda request: 'stats' not in request.GET and '/answers/' not in request.path_info)
def show_more(request, object_class, should_cache=True):
    def _load_objects(request, object_class):
        select_related_all = {
            Question: ['resource'],
            DecoratedAnswer: ['general_answer']
        }
        prefetch_related_all = {
            Set: ['questions'],
            Category: ['questions'],
            Question: [
                'question_options', 'question_options__option_images',
                'question_images', 'resource__resource_images', 'set_set', 'category_set'
            ]
        }
        select_related = select_related_all.get(object_class, [])
        prefetch_related = prefetch_related_all.get(object_class, [])
        if 'filter_column' in request.GET and 'filter_value' in request.GET:
            column = request.GET['filter_column']
            value = request.GET['filter_value']
            if value.isdigit():
                value = int(value)
            if column == 'category_id':
                objs = (get_object_or_404(Category, pk=value).questions)
                if len(select_related) > 0:
                    objs = objs.select_related(*select_related)
                objs = objs.prefetch_related(*prefetch_related).all()
            elif column == 'set_id':
                objs = (get_object_or_404(Set, pk=value).questions)
                if len(select_related) > 0:
                    objs = objs.select_related(*select_related)
                objs = objs.prefetch_related(*prefetch_related).all()
            else:
                objs = object_class.objects
                if len(select_related) > 0:
                    objs = objs.select_related(*select_related)
                objs = objs.prefetch_related(*prefetch_related).filter(**{column: value})
        else:
            objs = object_class.objects
            if len(select_related) > 0:
                objs = objs.select_related(*select_related)
            objs = objs.prefetch_related(*prefetch_related).all()
        if object_class == DecoratedAnswer:
            user_id = get_user_id(request)
            objs = objs.filter(general_answer__user_id=user_id).order_by('-general_answer__time')
        return objs

    return proso_common.views.show_more(
        request, _to_json, _load_objects, object_class,
        should_cache=should_cache, template='questions_json.html')


@ensure_csrf_cookie
@allow_lazy_user
@transaction.atomic
def practice(request):
    """
    Return the given number of questions to practice adaptively. In case of
    POST request, try to save the answer.

    GET parameters:
      limit:
        number of returned questions (default 10, maximum 100)
      category:
        identifier for the category which is meant to be practiced
      time:
        time in format '%Y-%m-%d_%H:%M:%S' used for practicing
      user:
        identifier for the practicing user (only for stuff users)
      stats:
        turn on the enrichment of the objects by some statistics
      html
        turn on the HTML version of the API

    POST parameters:
      question:
        identifer for the asked question
      answered:
        identifier for the answered option
      response_time:
        number of milliseconds the given user spent by answering the question
    """
    limit = min(int(request.GET.get('limit', 10)), 100)
    # prepare
    user = get_user_id(request)
    time = get_time(request)
    environment = get_environment()
    item_selector = get_item_selector()
    if is_time_overridden(request):
        environment.shift_time(time)
    category = request.GET.get('category', None)
    questions = None
    if category is not None:
        questions = get_object_or_404(Category, pk=category).questions.all()
    # save answers
    status = 200
    if request.method == 'POST':
        saved_answers = _save_answers(request)
        if not isinstance(saved_answers, list):
            return saved_answers
        status = 201
    # select a construct questions
    time_before_practice = time_lib()
    candidates = Question.objects.practice(item_selector, environment, user, time, limit, questions=questions)
    LOGGER.debug('choosing candidates for practice took %s seconds', (time_lib() - time_before_practice))
    json = _to_json(request, {
        'questions': map(lambda x: x.to_json(), candidates)
    })
    return render_json(request, json, template='questions_json.html', status=status, help_text=practice.__doc__)


@allow_lazy_user
def test(request):
    """
    Return questions to perform a test.

    GET parameters:
      time:
        time in format '%Y-%m-%d_%H:%M:%S' used for practicing
      user:
        identifier for the practicing user (only for stuff users)
      stats:
        turn on the enrichment of the objects by some statistics
      html
        turn on the HTML version of the API
    """
    user = get_user_id(request)
    time = get_time(request)
    question_set = Question.objects.test(user, time)
    candidates = (question_set.questions.
        select_related('resource').
        prefetch_related(
            'question_options', 'question_options__option_images',
            'question_images', 'resource__resource_images', 'set_set', 'category_set'
        ).all())
    json = _to_json(request, {
        'test': question_set.to_json(),
        'questions': map(lambda x: x.to_json(), candidates)
    })
    return render_json(request, json, template='questions_json.html', help_text=test.__doc__)


@allow_lazy_user
def test_evaluate(request, question_set_id):
    """
    Evaluate test answers:

    POST parameters:
      question:
        identifer for the asked question
      answered:
        identifier for the answered option
      response_time:
        number of milliseconds the given user spent by answering the question
    """
    question_set = get_object_or_404(Set, pk=question_set_id)
    if request.method == 'GET':
        questions = _to_json(request,
            list(question_set.
                questions.select_related('resource').
                prefetch_related(
                    'question_options', 'question_options__option_images',
                    'question_images', 'resource__resource_images', 'set_set', 'category_set'
                ).all()))
        return render(request, 'questions_test_evaluate.html', {'questions': questions}, help_text=test_evaluate.__doc__)
    elif request.method == 'POST':
        saved_answers = _save_answers(request, question_set=question_set)
        if not isinstance(saved_answers, list):
            return saved_answers
        test_evaluator = get_test_evaluator()
        answers_evaluated = test_evaluator.evaluate(saved_answers)
        questions = dict(map(
            lambda q: (q.item_id, q.id),
            list(Question.objects.filter(item_id__in=map(lambda a: a.general_answer.item_id, saved_answers)))))
        questions_evaluated = map(
            lambda (a, score): {'question_id': questions[a.general_answer.item_id], 'score': score},
            answers_evaluated)
        return render_json(
            request,
            {
                'score_to_pass': test_evaluator.score_to_pass(),
                'questions': questions_evaluated,
                'score_achieved': sum(map(lambda x: x['score'], questions_evaluated)),
                'score_max': test_evaluator.score_max(),
            },
            template='questions_json.html', help_text=test_evaluate.__doc__)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


@ensure_csrf_cookie
@allow_lazy_user
@transaction.atomic
def answer(request):
    """
    Save the answer.

    GET parameters:
      html
        turn on the HTML version of the API

    POST parameters:
      question:
        identifer for the asked question
      answered:
        identifier for the answered option
      response_time:
        number of milliseconds the given user spent by answering the question
    """
    if request.method == 'GET':
        return render(request, 'questions_answer.html', {}, help_text=answer.__doc__)
    elif request.method == 'POST':
        saved_answers = _save_answers(request)
        if not isinstance(saved_answers, list):
            return saved_answers
        if 'html' in request.GET and len(saved_answers) == 1:
            return redirect_pass_get(request, 'show_answer', id=saved_answers[0].id)
        else:
            return HttpResponse('ok', status=201)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


def _to_json(request, value):
    time_start = time_lib()
    if isinstance(value, list):
        json = map(lambda x: x if isinstance(x, dict) else x.to_json(), value)
    elif not isinstance(value, dict):
        json = value.to_json()
    else:
        json = value
    LOGGER.debug("converting value to simple JSON took %s seconds", (time_lib() - time_start))
    common_json_enrich.enrich_by_object_type(request, json, json_enrich.question, 'answer')
    if 'stats' in request.GET:
        common_json_enrich.enrich_by_object_type(
            request, json, models_json_enrich.prediction, ['question', 'set', 'category'])
    common_json_enrich.enrich_by_object_type(request, json, json_enrich.html, ['question', 'resource', 'option'])
    common_json_enrich.enrich_by_predicate(request, json, common_json_enrich.url, lambda x: True,
                                           ignore_get=['filter_column', 'filter_value'] + json_enrich.IGNORE_GET)
    common_json_enrich.enrich_by_object_type(request, json, json_enrich.questions, ['set', 'category'])
    common_json_enrich.enrich_by_object_type(request, json, json_enrich.test_evaluate, 'set')
    LOGGER.debug("converting value to JSON took %s seconds", (time_lib() - time_start))
    return json


def _save_answers(request, question_set=None):
    time_start = time_lib()
    question_key = 'question'
    answered_key = 'answered'
    response_time_key = 'response_time'
    if len(request.POST.getlist(question_key, [])) == 0:
        question_key += '[]'
        if len(request.POST.getlist(question_key, [])) == 0:
            return HttpResponseBadRequest('"question" is not defined')
    if len(request.POST.getlist(answered_key, [])) == 0:
        answered_key += '[]'
        if len(request.POST.getlist(answered_key, [])) == 0:
            return HttpResponseBadRequest('"answered" is not defined')
    if len(request.POST.getlist(response_time_key, [])) == 0:
        response_time_key += '[]'
        if len(request.POST.getlist(response_time_key, [])) == 0:
            return HttpResponseBadRequest('"response_time" is not defined')
    expected_question_ids = None
    if question_set:
        expected_question_ids = map(lambda q: q.id, question_set.questions.all())
    all_data = zip(
        map(lambda x: int(x) if x else None, request.POST.getlist(question_key)),
        map(lambda x: int(x) if x else None, request.POST.getlist(answered_key)),
        map(int, request.POST.getlist(response_time_key))
    )
    saved_answers = []
    answered_question_ids = []
    questions = dict(map(lambda q: (q.id, q), Question.objects.filter(pk__in=zip(*all_data)[0])))
    notnone_answered = filter(lambda x: x is not None, zip(*all_data)[1])
    correct_options = dict(zip(zip(*all_data)[0], Option.objects.get_correct_options(zip(*all_data)[0])))
    answered_options = dict(map(lambda o: (o.id, o), Option.objects.filter(pk__in=notnone_answered)))
    for question_id, option_answered_id, response_time in all_data:
        question = questions[question_id]
        answered_question_ids.append(question.id)
        option_answered = answered_options.get(option_answered_id, None)
        option_asked = correct_options[question_id]

        answer = Answer(
            user_id=request.user.id,
            item_id=question.item_id,
            item_asked_id=option_asked.item_id,
            item_answered_id=option_answered.item_id if option_answered else None,
            response_time=response_time)
        answer.save()
        decorated_answer = DecoratedAnswer(
            general_answer=answer,
            from_test=question_set)
        decorated_answer.save()
        saved_answers.append(decorated_answer)
    if expected_question_ids and sorted(expected_question_ids) != sorted(answered_question_ids):
        raise Exception("Answered questions do not match to the expected answered questions.")
    LOGGER.debug("saving of %s answers took %s seconds", len(all_data), (time_lib() - time_start))
    return saved_answers
