from django.shortcuts import get_object_or_404
from models import Question, Option, DecoratedAnswer, Set, Category, get_test_evaluator
from proso_models.models import Answer
from proso.django.response import render, render_json, redirect_pass_get
from django.views.decorators.csrf import ensure_csrf_cookie
from lazysignup.decorators import allow_lazy_user
from django.http import HttpResponse, HttpResponseBadRequest
from ipware.ip import get_ip
from django.db import transaction
import json_enrich
import proso_common.json_enrich as common_json_enrich
from proso.django.request import is_time_overriden, is_user_id_overriden, get_time, get_user_id
from proso_models.models import get_environment, get_recommendation
from proso_ab.models import Experiment, Value
import logging
from time import time as time_lib
from proso.django.cache import cache_page_conditional
import hashlib
from django.core.cache import cache
import json as json_lib


LOGGER = logging.getLogger('django.request')


def home(request):
    return render(request, 'questions_home.html', {})


@cache_page_conditional(condition=lambda request: 'stats' not in request.GET)
def show_one(request, object_class, id):
    """
    Return object of the given type with the specified identifier.

    GET parameters:
      user:
        identifier of the current user
      stats:
        turn on the enrichment of the objects by some statistics
      html
        turn on the HTML version of the API
    """
    obj = get_object_or_404(object_class, pk=id)
    json = _to_json(request, obj)
    return render_json(request, json, template='questions_json.html', help_text=show_one.__doc__)


@cache_page_conditional(condition=lambda request: 'stats' not in request.GET)
def show_more(request, object_class, should_cache=True):
    """
    Return list of objects of the given type.

    GET parameters:
      limit:
        number of returned questions (default 10, maximum 100)
      page:
        current page number
      filter_column:
        column name used to filter the results
      filter_value:
        value for the specified column used to filter the results
      user:
        identifier of the current user
      all:
        return all objects available instead of paging; be aware this parameter
        can be used only for objects for wich the caching is turned on
      db_orderby:
        database column which the result should be ordered by
      json_orderby:
        field of the JSON object which the result should be ordered by, it is
        less effective than the ordering via db_orderby; be aware this parameter
        can be used only for objects for which the caching is turned on
      desc
        turn on the descending order
      stats:
        turn on the enrichment of the objects by some statistics
      html
        turn on the HTML version of the API
    """
    if not should_cache and 'json_orderby' in request.GET:
        return render_json(request, {
            'error': "Can't order the result according to the JSON field, because the caching for this type of object is turned off. See the documentation."
            },
            template='questions_json.html', help_text=show_more.__doc__, status=501)
    if not should_cache and 'all' in request.GET:
        return render_json(request, {
            'error': "Can't get all objects, because the caching for this type of object is turned off. See the documentation."
            },
            template='questions_json.html', help_text=show_more.__doc__, status=501)
    time_start = time_lib()
    limit = min(int(request.GET.get('limit', 10)), 100)
    page = int(request.GET.get('page', 0))
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
            objs = (get_object_or_404(Category, pk=value).
                    questions.
                    select_related(*select_related).
                    prefetch_related(*prefetch_related).all())
        elif column == 'set_id':
            objs = (get_object_or_404(Set, pk=value).
                    questions.
                    select_related(*select_related).
                    prefetch_related(*prefetch_related).all())
        else:
            objs = (object_class.objects.
                    select_related(*select_related).
                    prefetch_related(*prefetch_related).filter(**{column: value}))
    else:
        objs = object_class.objects.select_related(*select_related).prefetch_related(*prefetch_related).all()
    if object_class == DecoratedAnswer:
        if is_user_id_overriden(request):
            user_id = int(request.GET['user'])
        else:
            user_id = request.user.id
        objs = objs.filter(general_answer__user_id=user_id).order_by('-general_answer__time')
    if 'db_orderby' in request.GET:
        objs = objs.order_by(('-' if 'desc' in request.GET else '') + request.GET['db_orderby'])
    if 'all' not in request.GET and 'json_orderby' not in request.GET:
        objs = objs[page * limit:(page + 1) * limit]
    cache_key = 'proso_questions_sql_json_%s' % hashlib.sha1(str(objs.query).decode('utf-8')).hexdigest()
    cached = cache.get(cache_key)
    if cached:
        list_objs = json_lib.loads(cached)
    else:
        list_objs = map(lambda x: x.to_json(), list(objs))
        cache.set(cache_key, json_lib.dumps(list_objs), 60 * 60 * 24 * 30)
    LOGGER.debug('loading objects in show_more view took %s seconds', (time_lib() - time_start))
    json = _to_json(request, list_objs)
    if 'json_orderby' in request.GET:
        time_before_json_sort = time_lib()
        json.sort(key=lambda x: (-1 if 'desc' in request.GET else 1) * x[request.GET['json_orderby']])
        if 'all' not in request.GET:
            json = json[page * limit:(page + 1) * limit]
        LOGGER.debug('sorting objects according to JSON field took %s seconds', (time_lib() - time_before_json_sort))
    return render_json(request, json, template='questions_json.html', help_text=show_more.__doc__)


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
    recommendation = get_recommendation()
    if is_time_overriden(request):
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
    # recommend
    time_before_practice = time_lib()
    candidates = Question.objects.practice(recommendation, environment, user, time, limit, questions=questions)
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
            request, json, json_enrich.prediction, ['question', 'set', 'category'])
    common_json_enrich.enrich_by_object_type(request, json, json_enrich.html, ['question', 'resource', 'option'])
    common_json_enrich.enrich_by_predicate(request, json, json_enrich.url, lambda x: True)
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
    ab_values = Value.objects.filter(id__in=map(lambda d: d['id'], Experiment.objects.get_values(request)))
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
            ip_address=get_ip(request),
            from_test=question_set)
        decorated_answer.save()
        for value in ab_values:
            decorated_answer.ab_values.add(value)
        decorated_answer.save()
        saved_answers.append(decorated_answer)
    if expected_question_ids and sorted(expected_question_ids) != sorted(answered_question_ids):
        raise Exception("Answered questions do not match to the expected answered questions.")
    LOGGER.debug("saving of %s answers took %s seconds", len(all_data), (time_lib() - time_start))
    return saved_answers
