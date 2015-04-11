from lazysignup.models import LazyUser
from django.contrib.auth.models import User
from lazysignup.utils import is_lazy_user
from social_auth.db.django_models import UserSocialAuth


def is_username_present(username):
    return User.objects.filter(username=username).exists()


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


def convert_lazy_user(user, with_username=True):
    LazyUser.objects.filter(user=user).delete()
    if with_username:
        if not is_user_named(user):
            raise Exception("The given user %s is not named!" % user.id)
        user.username = get_unused_username(user)
        user.save()


def is_user_lazy(user):
    return is_lazy_user(user)


def is_user_named(user):
    return user.first_name and user.last_name


def is_user_real(user):
    return bool(user.email)


def is_user_social(user):
    return UserSocialAuth.objects.filter(user=user).exists()
