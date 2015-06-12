import json
import logging
from time import time as time_lib
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import ensure_csrf_cookie
from lazysignup.decorators import allow_lazy_user

from proso.django.cache import cache_page_conditional
from proso.django.config import get_config
from proso.django.request import get_user_id, get_time, is_time_overridden
from proso.django.response import render, render_json
import proso_common.views
import proso_common.json_enrich as common_json_enrich
import proso_models.json_enrich as models_json_enrich
import proso_flashcards.json_enrich as flashcards_json_enrich
from proso_flashcards.models import Term, FlashcardAnswer, Flashcard, Context, Category
from proso_models.models import get_environment, get_predictive_model

LOGGER = logging.getLogger('django.request')


@cache_page_conditional(condition=lambda request: 'stats' not in request.GET)
def show_one(request, object_class, id):
    return proso_common.views.show_one(
        request, _to_json, object_class, id, template='flashcards_json.html')


@cache_page_conditional(
    condition=lambda request: 'stats' not in request.GET)
def show_more(request, object_class, should_cache=True):

    to_json_kwargs = {}
    if object_class == Flashcard and "without_contexts" in request.GET:
        to_json_kwargs['contexts'] = False

    def _load_objects(request, object_class):
        select_related_all = {
            Flashcard: [Flashcard.related_term(), Flashcard.related_context()]
        }
        prefetch_related_all = {
            settings.PROSO_FLASHCARDS.get("term_extension", Term): ["parents"],
            FlashcardAnswer: ["options"],
            Flashcard: ["categories"],
            settings.PROSO_FLASHCARDS.get("context_extension", Context): ["categories"],
        }
        select_related = select_related_all.get(object_class, [])
        prefetch_related = prefetch_related_all.get(object_class, [])
        objs = object_class.objects
        if len(select_related) > 0:
            objs = objs.select_related(*select_related)
        if 'filter_column' in request.GET and 'filter_value' in request.GET:
            column = request.GET['filter_column']
            value = request.GET['filter_value']
            if value.isdigit():
                value = int(value)

            objs = objs.prefetch_related(*prefetch_related).filter(**{column: value})
        else:
            objs = objs.prefetch_related(*prefetch_related).all()
        if object_class == FlashcardAnswer:
            user_id = get_user_id(request)
            objs = objs.filter(user_id=user_id).order_by('-time')
        if object_class == Flashcard:
            categories = json.loads(request.GET.get("categories", "[]"))
            contexts = json.loads(request.GET.get("contexts", "[]"))
            types = json.loads(request.GET.get("types", "[]"))
            avoid = json.loads(request.GET.get("avoid", "[]"))
            objs = objs.filter_fc(categories, contexts, types, avoid)
        if object_class == Flashcard or object_class == settings.PROSO_FLASHCARDS.get("term_extension", Term) or \
                object_class == settings.PROSO_FLASHCARDS.get("context_extension", Context) or object_class == Category:
            language = request.GET.get("language", request.LANGUAGE_CODE)
            objs = objs.filter(lang=language)
        return objs

    return proso_common.views.show_more(
        request, _to_json, _load_objects, object_class,
        should_cache=should_cache, template='flashcards_json.html', to_json_kwargs=to_json_kwargs)


@allow_lazy_user
def user_stats(request):
    """
    Get user statistics for selected flashcards groups

    time:
      time in format '%Y-%m-%d_%H:%M:%S' used for practicing
    user:
      identifier of the user (only for stuff users)
    username:
      username of user (only for users with public profile)
    filters:                -- use this or body
      json as in BODY
    mastered:
      use model to compute number of mastered FC - can be slowed

    BODY
      json in following format:
      {
        "#identifier":          -- custom identifier (str)
          {
            "categories": [],   -- list of ids (int) or identifiers (str) of categories
                                -- for union of multiple category intersections use list of lists
            "contexts": [],     -- list of ids (int) or identifiers (str) of contexts
            "types": [],        -- list of names (str) of types of terms
            "language": ,       -- language (str)
          },
        ...
      }
    """

    time_start = time_lib()
    response = {}
    data = None
    if request.method == "POST":
        data = json.loads(request.body)
    if "filters" in request.GET:
        data = json.loads(request.GET["filters"])
    if data is None:
        return render_json(request, {}, template='flashcards_user_stats.html', help_text=user_stats.__doc__)

    environment = get_environment()
    if is_time_overridden(request):
        environment.shift_time(get_time(request))
    if request.GET.get("username", False):
        try:
            user = User.objects.get(username=request.GET.get("username"), userprofile__public=True).id
        except ObjectDoesNotExist:
            return HttpResponseBadRequest("user not found or have not public profile")
    else:
        user = get_user_id(request)
    LOGGER.debug("user_stats - initialization took %s seconds", (time_lib() - time_start))

    time_start = time_lib()
    all_items, items_map = Flashcard.objects.filtered_ids_group(data, request.LANGUAGE_CODE)
    LOGGER.debug("user_stats - getting flashcards in groups took %s seconds", (time_lib() - time_start))

    time_start = time_lib()
    answers = dict(zip(all_items, environment.number_of_answers_more_items(all_items, user)))
    correct_answers = dict(zip(all_items, environment.number_of_correct_answers_more_items(all_items, user)))
    LOGGER.debug("user_stats - getting number of answers took %s seconds", (time_lib() - time_start))

    if request.GET.get("mastered"):
        time_start = time_lib()
        mastery_threshold = get_config("proso_models", "mastery_threshold", default=0.9)
        predictions = get_predictive_model().predict_more_items(environment, user, all_items, get_time(request))
        mastered = dict(zip(all_items, map(lambda p: p >= mastery_threshold, predictions)))
        LOGGER.debug("user_stats - getting predictions for flashcards took %s seconds", (time_lib() - time_start))

    time_start = time_lib()
    for identifier, items in items_map.items():
        if len(items) == 0:
            response[identifier] = {
                "filter": data[identifier],
                "number_of_flashcards": 0,
            }
        else:
            response[identifier] = {
                "filter": data[identifier],
                "number_of_flashcards": len(items),
                "number_of_practiced_flashcards": sum(answers[i] > 0 for i in items),
                "number_of_answers": sum(answers[i] for i in items),
                "number_of_correct_answers": sum(correct_answers[i] for i in items),
            }

        if request.GET.get("mastered"):
            response[identifier]["number_of_mastered_flashcards"]= sum(mastered[i] for i in items)
    LOGGER.debug("user_stats - extraction information to groups took %s seconds", (time_lib() - time_start))

    return render_json(request, response, template='flashcards_user_stats.html', help_text=user_stats.__doc__)


@allow_lazy_user
@transaction.atomic
def answer(request):
    """
    Save the answer.

    GET parameters:
      html
        turn on the HTML version of the API

    BODY
      json in following format:
      {
        "answer": #answer,                          -- for one answer
        "answers": [#answer, #answer, #answer ...]  -- for multiple answers
      }

      answer = {
        "flashcard_id": int,
        "flashcard_answered_id": int or null,
        "response_time": int,           -- response time in milliseconds
        "direction": "t2d" or "d2t",    -- direction of question: from term to description or conversely
        "option_ids": [ints],           -- optional - list of ids of terms, which were alternatives to correct one
        "meta": "str"                   -- optional information
        "time_gap": int                 -- waiting time in frontend in seconds
      }
    """

    if request.method == 'GET':
        return render(request, 'flashcards_answer.html', {}, help_text=answer.__doc__)
    elif request.method == 'POST':
        answers = _get_answers(request)
        if not isinstance(answers, list):
            return answers
        saved_answers = _save_answer(request, answers)
        if not isinstance(saved_answers, list):
            return saved_answers

        return HttpResponse(json.dumps([a.pk for a in saved_answers]), status=201)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


@ensure_csrf_cookie
@allow_lazy_user
@transaction.atomic
def practice(request):
    """
    Return the given number of questions to practice adaptively. In case of
    POST request, try to save the answer(s).

    GET parameters:
      categories:
      contexts:
        list of ids (int) or identifiers (str) of contexts to which flashcards selection will be restricted
      categories:
        list of ids (int) or identifiers (str) of categories to which flashcards selection will be restricted
        for union of multiple category intersections use list of lists
      types:
        list of names (str) of types of terms to which flashcards selection will be restricted
      language:
        language (str) of flashcards
      avoid:
        list of ids (int) of flashcards to avoid
      limit:
        number of returned questions (default 10, maximum 100)
      without_contexts:
        if context (boolean) is attached
      time:
        time in format '%Y-%m-%d_%H:%M:%S' used for practicing
      user:
        identifier for the practicing user (only for stuff users)
      stats:
        turn on the enrichment of the objects by some statistics
      html
        turn on the HTML version of the API

    BODY
      see answer resource
    """

    limit = min(int(request.GET.get('limit', 10)), 100)
    # prepare
    user = get_user_id(request)
    time = get_time(request)
    environment = get_environment()
    if is_time_overridden(request):
        environment.shift_time(time)

    # save answers
    if request.method == 'POST':
        answers = _get_answers(request)
        if not isinstance(answers, list):
            return answers
        saved_answers = _save_answer(request, answers)
        if not isinstance(saved_answers, list):
            return saved_answers

    # select
    categories = json.loads(request.GET.get("categories", "[]"))
    contexts = json.loads(request.GET.get("contexts", "[]"))
    types = json.loads(request.GET.get("types", "[]"))
    avoid = json.loads(request.GET.get("avoid", "[]"))
    with_contexts = "without_contexts" not in request.GET
    language = request.GET.get("language", request.LANGUAGE_CODE)

    time_before_practice = time_lib()
    candidates = Flashcard.objects.candidates_to_practice(categories, contexts, types, avoid, language)
    flashcards = Flashcard.objects.practice(environment, user, time, limit, candidates, language, with_contexts)
    LOGGER.debug('choosing candidates for practice took %s seconds', (time_lib() - time_before_practice))
    data = _to_json(request, {
        'flashcards': map(lambda x: x.to_json(categories=False, contexts=with_contexts), flashcards)
    })
    return render_json(request, data, template='flashcards_json.html', help_text=practice.__doc__)


def _get_answers(request):
    data = json.loads(request.body)
    if "answer" in data:
        answers = [data["answer"]]
    elif "answers" in data:
        answers = data["answers"]
    else:
        return HttpResponseBadRequest("Answer(s) not found")

    return answers


def _save_answer(request, answers):
    time_start = time_lib()
    saved_answers = []
    try:
        flashcard_ids = set()
        for a in answers:
            flashcard_ids.add(a["flashcard_id"])
            if a["flashcard_answered_id"] is not None:
                flashcard_ids.add(a["flashcard_answered_id"])
            if "option_ids" in a:
                flashcard_ids |= set(a["option_ids"])
        flashcards = dict(map(lambda fc: (fc.id, fc), Flashcard.objects.filter(pk__in=flashcard_ids)))
    except KeyError:
        return HttpResponseBadRequest("Flashcard or answered flashcard id not found")
    if len(flashcard_ids) != len(flashcards):
        return HttpResponseBadRequest("Invalid flashcard id (asked, answered or as option)")

    for a in answers:
        flashcard = flashcards[a["flashcard_id"]]
        flashcard_answered = flashcards[a["flashcard_answered_id"]] if a["flashcard_answered_id"] is not None else None
        if "response_time" in a:
            response_time = a["response_time"]
        else:
            return HttpResponseBadRequest("Response time not found")
        if "direction" in a:
            direction = a["direction"]
            if direction != FlashcardAnswer.FROM_DESCRIPTION and direction != FlashcardAnswer.FROM_TERM:
                return HttpResponseBadRequest(
                    "Invalid format of direction; allowed '{}' or '{}'"
                    .format(FlashcardAnswer.FROM_TERM, FlashcardAnswer.FROM_DESCRIPTION))
        else:
            return HttpResponseBadRequest("direction not found")

        db_answer = FlashcardAnswer(
            user_id=request.user.id,
            item_id=flashcard.item_id,
            item_asked_id=flashcard.item_id,
            item_answered_id=flashcard_answered.item_id if flashcard_answered else None,
            response_time=response_time,
            direction=direction,
            meta=a["meta"] if "meta" in a else None,
        )
        if "time_gap" in a:
            db_answer.time = datetime.now() - timedelta(seconds=a["time_gap"])
        db_answer.save()

        if "option_ids" in a:
            db_answer.options.add(flashcard)
            for option in a["option_ids"]:
                db_answer.options.add(flashcards[option])
            db_answer.save()

        saved_answers.append(db_answer)

    LOGGER.debug("saving of %s answers took %s seconds", len(answers), (time_lib() - time_start))

    return saved_answers


def _to_json(request, value):
    time_start = time_lib()
    if isinstance(value, list):
        json = map(lambda x: x if isinstance(x, dict) else x.to_json(), value)
    elif not isinstance(value, dict):
        json = value.to_json()
    else:
        json = value
    LOGGER.debug("converting value to simple JSON took %s seconds", (time_lib() - time_start))
    common_json_enrich.enrich_by_predicate(request, json, common_json_enrich.url, lambda x: True,
                                       ignore_get=['filter_column', 'filter_value', 'categories', 'contexts', 'types'])
    if 'environment' in request.GET:
        common_json_enrich.enrich_by_object_type(request, json, common_json_enrich.env_variables,
                                                 ["fc_term"],
                                                 skip_nested=True,
                                                 variable_type=[("parent", None, True), ("child", None, True)])
        common_json_enrich.enrich_by_object_type(request, json, common_json_enrich.env_variables,
                                                 ["fc_category"],
                                                 skip_nested=True,
                                                 variable_type=[("parent", None, True), ("child", None, True)])
        common_json_enrich.enrich_by_object_type(request, json, common_json_enrich.env_variables,
                                                 ["fc_flashcard"],
                                                 skip_nested=True,
                                                 variable_type=[("parent", None, True)])
    if 'stats' in request.GET:
        common_json_enrich.enrich_by_object_type(
            request, json, models_json_enrich.prediction, ['fc_flashcard', 'fc_term'], skip_nested=True)
        common_json_enrich.enrich_by_object_type(
            request, json, flashcards_json_enrich.practiced, ['fc_flashcard'], skip_nested=True)
        common_json_enrich.enrich_by_object_type(
            request, json, flashcards_json_enrich.avg_prediction, ['fc_category', 'fc_term', 'fc_context'], skip_nested=True)
    LOGGER.debug("converting value to JSON took %s seconds", (time_lib() - time_start))
    return json
