import json
import logging
from time import time as time_lib
from django.conf import settings

from django.db import transaction

from django.http import HttpResponse, HttpResponseBadRequest
from lazysignup.decorators import allow_lazy_user

from proso.django.cache import cache_page_conditional
from proso.django.request import get_user_id

from proso.django.response import render
import proso_common.views
import proso_common.json_enrich as common_json_enrich
from proso_flashcards.models import Term, FlashcardAnswer, Flashcard

LOGGER = logging.getLogger('django.request')


@cache_page_conditional(condition=lambda request: 'stats' not in request.GET)
def show_one(request, object_class, id):
    return proso_common.views.show_one(
        request, _to_json, object_class, id, template='flashcards_json.html')


@cache_page_conditional(
    condition=lambda request: 'stats' not in request.GET)
def show_more(request, object_class, should_cache=True):
    def _load_objects(request, object_class):
        select_related_all = {
        }
        prefetch_related_all = {
            settings.PROSO_FLASHCARDS.get("term_extension", Term): ["parents"],
            FlashcardAnswer: ["options"],
        }
        select_related = select_related_all.get(object_class, [])
        prefetch_related = prefetch_related_all.get(object_class, [])
        if 'filter_column' in request.GET and 'filter_value' in request.GET:
            column = request.GET['filter_column']
            value = request.GET['filter_value']
            if value.isdigit():
                value = int(value)
            objs = (object_class.objects.
                    select_related(*select_related).
                    prefetch_related(*prefetch_related).filter(**{column: value}))
        else:
            objs = object_class.objects.select_related(*select_related). \
                prefetch_related(*prefetch_related).all()
        if object_class == FlashcardAnswer:
            user_id = get_user_id(request)
            objs = objs.filter(user_id=user_id).order_by('-time')
        return objs

    return proso_common.views.show_more(
        request, _to_json, _load_objects, object_class,
        should_cache=should_cache, template='flashcards_json.html')


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
        "term_answered_id": int,
        "response_time": int,           -- response time in milliseconds
        "direction": "t2d" or "d2t",    -- direction of question: from term to description or conversely
        "option_ids": [ints],           -- optional - list of ids of terms, which were alternatives to correct one
        "meta": "str"                   -- optional information
      }
    """

    if request.method == 'GET':
        return render(request, 'flashcards_answer.html', {}, help_text=answer.__doc__)
    elif request.method == 'POST':
        data = json.loads(request.body)
        if "answer" in data:
            answers = [data["answer"]]
        elif "answers" in data:
            answers = data["answers"]
        else:
            return HttpResponseBadRequest("Answer(s) not found")
        saved_answers = _save_answer(request, answers)

        if not isinstance(saved_answers, list):
            return saved_answers

        return HttpResponse(json.dumps([a.pk for a in saved_answers]), status=201)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


def _save_answer(request, answers):
    time_start = time_lib()
    saved_answers = []
    try:
        flashcard_ids = set([a["flashcard_id"] for a in answers])
        flashcards = dict(map(lambda fc: (fc.id, fc),
                              Flashcard.objects.filter(pk__in=flashcard_ids)
                              .select_related("term")))
    except KeyError:
        return HttpResponseBadRequest("Flashcard id not found")
    if len(flashcard_ids) != len(flashcards):
        return HttpResponseBadRequest("Invalid flashcard id")

    try:
        terms_ids = set()
        for a in answers:
            if a["term_answered_id"] is not None:
                terms_ids.add(a["term_answered_id"])
            if "option_ids" in a:
                terms_ids |= set(a["option_ids"])
        terms = dict(map(lambda t: (t.id, t),
                         Term.objects.filter(pk__in=terms_ids)))
    except KeyError:
        return HttpResponseBadRequest("Answered term id not found")
    if len(terms_ids) != len(terms):
        return HttpResponseBadRequest("Invalid term id (answered or as option)")

    for a in answers:
        flashcard = flashcards[a["flashcard_id"]]
        term_answered = terms[a["term_answered_id"]] if a["term_answered_id"] is not None else None
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
            item_asked_id=flashcard.term.item_id,
            item_answered_id=term_answered.item_id if term_answered else None,
            response_time=response_time,
            direction=direction,
            meta=a["meta"] if "meta" in a else None,
        )
        db_answer.save()

        if "option_ids" in a:
            for option in a["option_ids"]:
                db_answer.options.add(terms[option])
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
                                           ignore_get=['filter_column', 'filter_value'])
    if 'environment' in request.GET:
        common_json_enrich.enrich_by_object_type(request, json, common_json_enrich.env_variables,
                                                 ["fc_term"], variable_type=[("parent", None, True)])
        common_json_enrich.enrich_by_object_type(request, json, common_json_enrich.env_variables,
                                                 ["fc_category"],
                                                 variable_type=[("parent", None, True), ("child", None, True)])
    LOGGER.debug("converting value to JSON took %s seconds", (time_lib() - time_start))
    return json
