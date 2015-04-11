# -*- coding: utf-8 -*-
from django.conf import settings
from flatblocks.models import FlatBlock
from proso.django.auth import is_user_named, is_user_lazy, convert_lazy_user


class StaticFiles():

    @staticmethod
    def add_hash(files):
        return [f + "?hash=" + StaticFiles.get_hash_od_file(f) for f in files]

    @staticmethod
    def get_hash_od_file(f):
        return settings.HASHES.get(f, '')


def get_user(request):
    user = request.user
    if user and is_user_lazy(user) and is_user_named(user):
        convert_lazy_user(request.user)
    username = user.username if user and not is_user_lazy(user) else ''
    response = {
        'username': username,
    }
    return response


def get_flatblock(slug):
    try:
        return FlatBlock.objects.get(slug=slug).content
    except FlatBlock.DoesNotExist:
        return ''


def get_page_title():
    if settings.ON_PRODUCTION:
        title = ''
    elif settings.ON_STAGING:
        title = 'Stage - '
    else:
        title = 'Loc - '
    title += get_flatblock('title') + ' - ' + get_flatblock('subtitle')
    return title
