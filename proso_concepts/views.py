import logging

import datetime
from django.contrib.admin.views.decorators import staff_member_required
from lazysignup.decorators import allow_lazy_user

import proso_common.views
from proso.django.cache import cache_page_conditional
from proso.django.enrichment import enrich_json_objects_by_object_type
from proso.django.request import get_user_id, load_query_json, get_language
from proso.django.response import render_json
from proso_concepts.models import Concept, UserStat

LOGGER = logging.getLogger('django.request')


@cache_page_conditional(condition=lambda request, args, kwargs: 'stats' not in request.GET)
def show_one(request, object_class, id):
    return proso_common.views.show_one(
        request, enrich_json_objects_by_object_type, object_class, id, template='concepts_json.html')


@cache_page_conditional(condition=lambda request, args, kwargs: 'stats' not in request.GET)
def show_more(request, object_class, should_cache=True):

    to_json_kwargs = {}

    def _load_objects(request, object_class):
        objs = object_class.objects.prepare_related()
        if 'filter_column' in request.GET and 'filter_value' in request.GET:
            column = request.GET['filter_column']
            value = request.GET['filter_value']
            if value.isdigit():
                value = int(value)
            objs = objs.filter(**{column: value})
        else:
            objs = objs.all()
        if object_class == Concept:
            objs = objs.filter(active=True, lang=get_language(request))
        return objs

    return proso_common.views.show_more(
        request, enrich_json_objects_by_object_type, _load_objects, object_class,
        should_cache=should_cache, template='concepts_json.html', to_json_kwargs=to_json_kwargs)


@allow_lazy_user
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
    data = UserStat.objects.get_user_stats(user, language, concepts)
    return render_json(request, data, template='concepts_json.html', help_text=user_stats.__doc__)


@staff_member_required
def user_stats_bulk(request):
    """
    Get statistics for selected users and concepts

    since:
      time as timestamp - get stats changed since
    users:
      list of identifiers of users
    concepts (Optional):
      list of identifiers of concepts
    language:
      language of concepts
    """

    language = get_language(request)
    users = load_query_json(request.GET, "users")
    since = None
    if 'since' in request.GET:
        since = datetime.datetime.fromtimestamp(int(request.GET['since']))
    concepts = None
    if "concepts" in request.GET:
        concepts = Concept.objects.filter(lang=language, active=True,
                                          identifier__in=load_query_json(request.GET, "concepts"))
    stats = UserStat.objects.get_user_stats(users, language, concepts=concepts, since=since)
    data = {"users": []}
    for user, s in stats.items():
        data["users"].append({
            "user_id": user,
            "concepts": s,
        })
    return render_json(request, data, template='concepts_json.html', help_text=user_stats_bulk.__doc__)
