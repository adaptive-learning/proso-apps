from django.shortcuts import render, get_object_or_404
from models import Question, Option, DecoratedAnswer, Set, Category
from proso_models.models import Answer
from proso.django.response import render_json, redirect_pass_get
from django.views.decorators.csrf import ensure_csrf_cookie
from lazysignup.decorators import allow_lazy_user
from django.http import HttpResponse, HttpResponseBadRequest
from ipware.ip import get_ip
from django.db import transaction
import json_enrich
import proso_common.json_enrich as common_json_enrich
from proso.django.request import get_time, get_user_id
from proso_models.models import get_environment, get_recommendation


def home(request):
    return render(request, 'questions_home.html', {})


def show_one(request, object_class, id):
    obj = get_object_or_404(object_class, pk=id)
    json = _to_json(request, obj)
    return render_json(request, json, template='questions_json.html')


def show_more(request, object_class, all=False):
    limit = 100
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
        if 'user' in request.GET and request.user.is_staff():
            user_id = int(request.GET['user'])
        else:
            user_id = request.user.id
        objs = objs.filter(general_answer__user_id=user_id).order_by('-general_answer__time')
    if not all:
        objs = objs[page * limit:(page + 1) * limit]
    json = _to_json(request, list(objs))
    return render_json(request, json, template='questions_json.html')


def practice(request, n):
    user = get_user_id(request)
    time = get_time(request)
    environment = get_environment()
    recommendation = get_recommendation()
    if request.user.is_staff and 'time' in request.GET:
        environment.shift_time(time)
    category = request.GET.get('category', None)
    questions = None
    if category is not None:
        questions = get_object_or_404(Category, pk=category).questions.all()
    candidates = Question.objects.practice(recommendation, environment, user, time, int(n), questions=questions)
    json = _to_json(request, candidates)
    return render_json(request, json, template='questions_json.html')


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

        if 'html' in request.GET:
            return redirect_pass_get(request, 'show_answer', id=decorated_answer.id)
        else:
            return HttpResponse('ok', status=201)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


def _to_json(request, value):
    if isinstance(value, list):
        json = map(lambda x: x.to_json(), value)
    else:
        json = value.to_json()
    common_json_enrich.enrich_by_object_type(request, json, json_enrich.question, 'answer')
    if 'stats' in request.GET:
        for object_type in ['question', 'category', 'set']:
            common_json_enrich.enrich_by_object_type(request, json, json_enrich.prediction, object_type)
    for enricher in [json_enrich.url, json_enrich.html, json_enrich.questions]:
        json = common_json_enrich.enrich(request, json, enricher)
    return json
