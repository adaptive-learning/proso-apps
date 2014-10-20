# -*- coding: utf-8 -*-
from django.conf import settings
from lazysignup.models import LazyUser
from django.contrib.auth.models import User
from flatblocks.models import FlatBlock


class StaticFiles():

    @staticmethod
    def add_hash(files):
        return [f + "?hash=" + StaticFiles.get_hash_od_file(f) for f in files]

    @staticmethod
    def get_hash_od_file(f):
        return settings.HASHES.get(f, '')


def convert_lazy_user(user):
    LazyUser.objects.filter(user=user).delete()
    user.username = get_unused_username(user)
    user.save()


def is_username_present(username):
    if User.objects.filter(username=username).count():
        return True
    return False


def is_lazy(user):
    if user.is_anonymous() or len(user.username) != 30:
        return False
    return bool(LazyUser.objects.filter(user=user).count() > 0)


def is_named(user):
    return user.first_name and user.last_name


def get_unused_username(user):
    condition = True
    append = ""
    i = 2
    while condition:
        username = user.first_name + user.last_name + append
        condition = is_username_present(username)
        append = '{0}'.format(i)
        i = i + 1
    return username


def get_user(request):
    user = request.user
    if user and is_lazy(user) and is_named(user):
        convert_lazy_user(request.user)
    username = user.username if user and not is_lazy(user) else ''
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
