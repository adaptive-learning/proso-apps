from django.conf import settings
from proso.django.cache import cache_page_conditional
from proso.django.enrichment import enrich_json_objects_by_object_type
from proso.django.request import get_language
from proso_flashcards.models import Term, FlashcardAnswer, Flashcard, Context, Category
from proso_models.models import get_filter, Item
from proso_user.models import get_user_id
import logging
import proso_common.views


LOGGER = logging.getLogger('django.request')


@cache_page_conditional(condition=lambda request, args, kwargs: 'stats' not in request.GET)
def show_one(request, object_class, id):
    return proso_common.views.show_one(
        request, enrich_json_objects_by_object_type, object_class, id, template='flashcards_json.html')


@cache_page_conditional(
    condition=lambda request, args, kwargs: 'stats' not in request.GET and kwargs['object_class'] != FlashcardAnswer)
def show_more(request, object_class, should_cache=True):

    to_json_kwargs = {}

    def _load_objects(request, object_class):
        objs = object_class.objects
        if hasattr(objs, 'prepare_related'):
            objs = objs.prepare_related()
        db_filter = proso_common.views.get_db_filter(request)
        objs = objs.all() if db_filter is None else objs.filter(**db_filter)
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
        if object_class in [Flashcard, Category, Context]:
            objs = objs.filter(active=True)
        return objs

    return proso_common.views.show_more(
        request, enrich_json_objects_by_object_type, _load_objects, object_class,
        should_cache=should_cache, template='flashcards_json.html', to_json_kwargs=to_json_kwargs)
