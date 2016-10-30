from proso.django.cache import cache_page_conditional
from proso.django.enrichment import enrich_json_objects_by_object_type
from proso.django.request import get_language
from proso_tasks.models import TaskAnswer
import logging
import proso_common.views


LOGGER = logging.getLogger('django.request')


@cache_page_conditional(condition=lambda request, args, kwargs: 'stats' not in request.GET)
def show_one(request, object_class, id):
    return proso_common.views.show_one(
        request, enrich_json_objects_by_object_type, object_class, id, template='tasks_json.html')


@cache_page_conditional(
    condition=lambda request, args, kwargs: 'stats' not in request.GET and kwargs['object_class'] != TaskAnswer)
def show_more(request, object_class, should_cache=True):

    to_json_kwargs = {}

    def _load_objects(request, object_class):
        objs = object_class.objects
        if hasattr(objs, 'prepare_related'):
            objs = objs.prepare_related().filter(active=True)
        db_filter = proso_common.views.get_db_filter(request)
        objs = objs.filter(lang=get_language(request)) if db_filter is None else objs.filter(**db_filter)
        return objs

    return proso_common.views.show_more(
        request, enrich_json_objects_by_object_type, _load_objects, object_class,
        should_cache=should_cache, template='tasks_json.html', to_json_kwargs=to_json_kwargs)
