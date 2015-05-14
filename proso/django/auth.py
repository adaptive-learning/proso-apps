from lazysignup.models import LazyUser
from django.contrib.auth.models import User
from social_auth.db.django_models import UserSocialAuth
from lazysignup.signals import converted
from django.template.defaultfilters import slugify


def is_username_present(username):
    return User.objects.filter(username=username).exists()


def get_unused_username(user):
    condition = True
    append = ""
    i = 2
    while condition:
        username = slugify('%s_%s%s' % (user.first_name, user.last_name, append))
        condition = is_username_present(username)
        append = '_%s' % str(i)
        i = i + 1
    return username


def convert_lazy_user(user):
    LazyUser.objects.filter(user=user).delete()
    LazyUser.objects.update()
    converted.send(None, user=user)


def name_lazy_user(user, save=True):
    if not is_user_named(user):
        raise Exception("The given user %s is not named!" % user.id)
    user.username = get_unused_username(user)
    if save:
        user.save()


def is_user_lazy(user):
    if user.is_anonymous():
        return False
    return LazyUser.objects.filter(user=user).exists()


def is_user_named(user):
    return user.first_name and user.last_name


def is_user_real(user):
    return bool(user.email)


def is_user_social(user):
    return UserSocialAuth.objects.filter(user=user).exists()
