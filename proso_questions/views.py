from django.shortcuts import render, redirect, get_object_or_404
from models import Question, Option, DecoratedAnswer
from proso_models.models import Answer
from proso.django.response import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from lazysignup.decorators import allow_lazy_user
from django.http import HttpResponse, HttpResponseBadRequest
from ipware.ip import get_ip
from django.db import transaction
import json_enrich
import proso.util
from django.conf import settings


def home(request):
    return render(request, 'questions_home.html', {})


def show_one(request, object_class, id):
    obj = get_object_or_404(object_class, pk=id)
    json = _to_json(request, obj)
    if 'html' in request.GET:
        return render(
            request, 'questions_json.html',
            {'json': json})
    else:
        return JsonResponse(json)


def show_more(request, object_class, all=False):
    limit = 100
    page = int(request.GET.get('page', 0))
    related = {
        Question: ['category', 'question_set'],
        DecoratedAnswer: ['general_answer']
    }
    select_related = related.get(object_class, [])
    if 'filter_column' in request.GET and 'filter_value' in request.GET:
        column = request.GET['filter_column']
        value = request.GET['filter_value']
        if value.isdigit():
            value = int(value)
        objs = object_class.objects.select_related(*select_related).filter(
            **{column: value})
    else:
        objs = object_class.objects.select_related(*select_related).all()
    if object_class == DecoratedAnswer:
        if 'user' in request.GET and request.user.is_staff():
            user_id = int(request.GET['user'])
        else:
            user_id = request.user.id
        objs = objs.filter(general_answer__user_id=user_id).order_by('-general_answer__time')
    if not all:
        objs = objs[page * limit:(page + 1) * limit]
    json = _to_json(request, list(objs))
    if 'html' in request.GET:
        return render(
            request, 'questions_json.html',
            {'json': json})
    else:
        return JsonResponse(json)


def candidates(request, user, n):
    category = request.GET.get('category', None)
    question_set = request.GET.get('question_set', None)
    questions = None
    if category is not None:
        questions = Question.objects.filter(category_id=category)
    if question_set is not None:
        if questions is None:
            questions = Question.objects
        questions = questions.filter(question_set_id=question_set)
    candidates = Question.objects.candidates(int(user), int(n), questions=questions)
    json = _to_json(request, candidates)
    if request.GET.get('html', False):
        return render(
            request, 'questions_json.html',
            {'json': json})
    else:
        return JsonResponse(map(lambda q: q.to_json(), candidates))


@ensure_csrf_cookie
@allow_lazy_user
@transaction.atomic
def answer(request):
    if request.method == 'GET':
        return render(request, 'questions_answer.html', {})
    elif request.method == 'POST':
        if 'question' not in request.POST or not request.POST['question']:
            return HttpResponseBadRequest('"question" is not defined')
        if 'answered' not in request.POST or not request.POST['answered']:
            return HttpResponseBadRequest('"answered" is not defined')
        if 'response_time' not in request.POST or not request.POST['response_time']:
            return HttpResponseBadRequest('"response_time" is not defined')
        question = get_object_or_404(Question, pk=request.POST['question'])
        option_answered = get_object_or_404(Option, pk=request.POST['answered'])
        option_asked = Option.objects.get_correct_option(question)
        response_time = int(request.POST['response_time'])

        answer = Answer(
            user_id=request.user.id,
            item_id=question.item_id,
            item_asked_id=option_asked.item_id,
            item_answered_id=option_answered.item_id,
            response_time=response_time)
        answer.save()
        decorated_answer = DecoratedAnswer(
            general_answer=answer,
            ip_address=get_ip(request))
        decorated_answer.save()

        predictive_model = proso.util.instantiate(settings.PROSO_PREDICTIVE_MODEL)
        environment = proso.util.instantiate(settings.PROSO_ENVIRONMENT)

        predictive_model.predict_and_update(
            environment,
            request.user.id,
            question.item_id,
            option_asked.item_id,
            option_answered.item_id,
            answer.time)
        if 'html' in request.GET:
            response = redirect('show_answer', id=decorated_answer.id)
            response['location'] += '?html'
            return response
        else:
            return HttpResponse('ok', status=201)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


def _to_json(request, value):
    if isinstance(value, list):
        json = map(lambda x: x.to_json(), value)
    else:
        json = value.to_json()
    json_enrich.enrich_by_object_type(request, json, json_enrich.question, 'answer')
    json_enrich.enrich_by_object_type(request, json, json_enrich.options, 'question')
    for object_type in ['option', 'resource', 'question']:
        json_enrich.enrich_by_object_type(request, json, json_enrich.images, object_type)
    if 'stats' in request.GET:
        for object_type in ['question', 'set', 'category']:
            json_enrich.enrich_by_object_type(request, json, json_enrich.prediction, object_type)

    for enricher in [json_enrich.url, json_enrich.html, json_enrich.questions]:
        json = json_enrich.enrich(request, json, enricher)
    return json
