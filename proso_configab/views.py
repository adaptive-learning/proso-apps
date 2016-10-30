from .models import Experiment
from proso.django.enrichment import enrich_json_objects_by_object_type
import logging
import proso_common.views


LOGGER = logging.getLogger('django.request')


def show_one(request, object_class, id):
    return proso_common.views.show_one(
        request, enrich_json_objects_by_object_type, object_class, id, template='configab_json.html')


def show_more(request, object_class, should_cache=True):

    def _load_objects(request, object_class):
        select_related_all = {}
        prefetch_related_all = {
            Experiment: ['experimentsetup_set__values', 'experimentsetup_set__values__variable']
        }
        select_related = select_related_all.get(object_class, [])
        prefetch_related = prefetch_related_all.get(object_class, [])
        objs = object_class.objects
        if len(select_related) > 0:
            objs = objs.select_related(*select_related)
        objs.prefetch_related(*prefetch_related)
        db_filter = proso_common.views.get_db_filter(request)
        objs = objs.all() if db_filter is None else objs.filter(**db_filter)
        return objs

    return proso_common.views.show_more(
        request, enrich_json_objects_by_object_type, _load_objects, object_class,
        should_cache=should_cache, template='configab_json.html', to_json_kwargs={})
