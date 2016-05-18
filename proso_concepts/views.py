import logging

import datetime
from collections import defaultdict
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from lazysignup.decorators import allow_lazy_user
from social.apps.django_app.default.models import UserSocialAuth

import proso_common.views
from proso.django.cache import cache_page_conditional
from proso.django.enrichment import enrich_json_objects_by_object_type
from proso.django.request import get_user_id, load_query_json, get_language
from proso.django.response import render_json
from proso_concepts.models import Concept, UserStat, Tag

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


def user_stats_api(request, provider):
    """
    Get statistics for selected Edookit users

    key:
      api key
    since:
      time as timestamp - get stats changed since
    """

    if 'key' not in request.GET or provider not in settings.USER_STATS_API_KEY \
            or request.GET['key'] != settings.USER_STATS_API_KEY[provider]:
        return HttpResponse('Unauthorized', status=401)
    since = None
    if 'since' in request.GET:
        since = datetime.datetime.fromtimestamp(int(request.GET['since']))

    social_users = list(UserSocialAuth.objects.filter(provider=provider).select_related('user'))
    user_map = {u.user.id: u for u in social_users}
    stats = UserStat.objects.get_user_stats([u.user for u in social_users], lang=None, since=since, recalculate=False)
    data = {"users": []}
    for user, s in stats.items():
        data["users"].append({
            "user_id": user_map[user].uid,
            "concepts": s,
        })
    return render_json(request, data, template='concepts_json.html', help_text=user_stats_bulk.__doc__)


def tag_values(request):
    """
    Get tags types and values with localized names

    language:
      language of tags
    """

    data = defaultdict(lambda: {"values": {}})
    for tag in Tag.objects.filter(lang=get_language(request)):
        data[tag.type]["name"] = tag.type_name
        data[tag.type]["values"][tag.value] = tag.value_name

    return render_json(request, data, template='concepts_json.html', help_text=tag_values.__doc__)
