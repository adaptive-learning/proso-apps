from django.conf import settings
from proso.django.cache import cache_page_conditional
from proso.django.enrichment import enrich_json_objects_by_object_type, register_object_type_enricher
from proso.django.request import get_language
from proso_flashcards.models import Term, FlashcardAnswer, Flashcard, Context, Category
from proso_models.models import get_filter, Item
from proso_user.models import get_user_id
import logging
import proso_common.views
import proso_flashcards.json_enrich as flashcards_json_enrich
import proso_models.json_enrich as models_json_enrich


LOGGER = logging.getLogger('django.request')


@cache_page_conditional(condition=lambda request, args, kwargs: 'stats' not in request.GET)
def show_one(request, object_class, id):
    return proso_common.views.show_one(
        request, enrich_json_objects_by_object_type, object_class, id, template='flashcards_json.html')


@cache_page_conditional(
    condition=lambda request, args, kwargs: 'stats' not in request.GET and kwargs['object_class'] != FlashcardAnswer)
def show_more(request, object_class, should_cache=True):

    to_json_kwargs = {}
    if object_class == Flashcard and "without_contexts" in request.GET:
        to_json_kwargs['contexts'] = False
    if issubclass(object_class, Context) and 'without_content' in request.GET:
        to_json_kwargs['with_content'] = False

    def _load_objects(request, object_class):
        objs = object_class.objects
        if hasattr(objs, 'prepare_related'):
            objs = objs.prepare_related()
        if 'filter_column' in request.GET and 'filter_value' in request.GET:
            column = request.GET['filter_column']
            value = request.GET['filter_value']
            if value.isdigit():
                value = int(value)
            objs = objs.filter(**{column: value})
        else:
            objs = objs.all()
        if object_class == FlashcardAnswer:
            user_id = get_user_id(request, allow_override=True)
            item_filter = get_filter(request)
            if len(item_filter) != 0:
                item_ids = Item.objects.filter_all_reachable_leaves(item_filter, get_language(request))
                objs = objs.filter(item_asked__in=item_ids)
            objs = objs.filter(user_id=user_id).order_by('-time')
        if object_class == Flashcard or object_class == settings.PROSO_FLASHCARDS.get("term_extension", Term) or \
                object_class == settings.PROSO_FLASHCARDS.get("context_extension", Context) or object_class == Category:
            language = get_language(request)
            objs = objs.filter(lang=language)
        return objs

    return proso_common.views.show_more(
        request, enrich_json_objects_by_object_type, _load_objects, object_class,
        should_cache=should_cache, template='flashcards_json.html', to_json_kwargs=to_json_kwargs)


################################################################################
# Enrichers
################################################################################

register_object_type_enricher(['fc_answer'], flashcards_json_enrich.answer_flashcards)
register_object_type_enricher(['fc_flashcard'], models_json_enrich.prediction)
register_object_type_enricher(['fc_flashcard', 'fc_category', 'fc_term', 'fc_context'], models_json_enrich.number_of_answers)
register_object_type_enricher(['fc_category', 'fc_term', 'fc_context'], models_json_enrich.avg_prediction)
register_object_type_enricher(['question'], flashcards_json_enrich.answer_type)
register_object_type_enricher(['question'], flashcards_json_enrich.question_type, priority=-1000)
register_object_type_enricher(['question'], flashcards_json_enrich.options, dependencies=[flashcards_json_enrich.question_type], priority=-1000)
