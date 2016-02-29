import logging
from collections import defaultdict

import proso_common.views
# from proso_common import json_enrich
from proso.django.cache import cache_page_conditional
from proso.django.enrichment import enrich_json_objects_by_object_type
from proso.django.request import get_user_id, load_query_json, get_language
from proso.django.response import render_json
from proso_concepts.models import Concept, Tag, UserStat

LOGGER = logging.getLogger('django.request')


@cache_page_conditional(condition=lambda request, args, kwargs: 'stats' not in request.GET)
def show_one(request, object_class, id):
    return proso_common.views.show_one(
        request, enrich_json_objects_by_object_type, object_class, id, template='concepts_json.html')


@cache_page_conditional(condition=lambda request, args, kwargs: 'stats' not in request.GET)
def show_more(request, object_class, should_cache=True):

    to_json_kwargs = {}

    def _load_objects(request, object_class):
        select_related_all = {
            Concept: [],
        }
        prefetch_related_all = {
            Concept: ["tags", "actions"],
            Tag: ["concepts"],
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
        if object_class == Concept:
            objs = objs.filter(active=True)
        return objs

    return proso_common.views.show_more(
        request, enrich_json_objects_by_object_type, _load_objects, object_class,
        should_cache=should_cache, template='concepts_json.html', to_json_kwargs=to_json_kwargs)


def user_stats(request):
    """
    JSON of user stats of the user

    GET parameters:
      html (bool):
        turn on the HTML version of the API, defaults to false
      user (int):
        identifier of the user, defaults to logged user
      concepts (list):
        list of identifiers of concepts, defaults to all concepts
      lang (str):
        language of requested concepts, defaults to language from django
    """
    user = get_user_id(request)
    language = get_language(request)

    concepts = None    # meaning all concept
    if "concepts" in request.GET:
        concepts = Concept.objects.filter(lang=language, active=True,
                                          identifier__in=load_query_json(request.GET, "concepts"))

    data = defaultdict(lambda: {})
    for user_stat in UserStat.get_user_stats(user, language, concepts):
        data[user_stat.concept.identifier][user_stat.stat] = user_stat.value

    return render_json(request, data, template='concepts_json.html', help_text=user_stats.__doc__)


################################################################################
# Enrichers
################################################################################

# register_object_type_enricher(["concept", "tag"], json_enrich.url)
