import json
from urllib.request import urlopen, Request
import time
from django.contrib.auth.models import User
from social.apps.django_app.default.models import UserSocialAuth
from social.backends.oauth import BaseOAuth2
from proso.django.auth import get_unused_username


class EdookitOAuth2(BaseOAuth2):
    """Edookit OAuth authentication backend"""

    name = 'edookit'
    AUTHORIZATION_URL = 'https://oauth.edookit.net/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://oauth.edookit.net/oauth/token'
    ACCESS_TOKEN_METHOD = 'POST'
    ID_KEY = 'person_id'
    EXTRA_DATA = [
        ('refresh_token', 'refresh_token'),
        ('expires_in', 'expires_in'),
        ('grade', 'grade'),
        ('class_id', 'class_id'),
        ('class_name', 'class_name'),
        ('organization_id', 'organization_id'),
        ('organization_name', 'organization_name'),
        ('organization_address', 'organization_address'),
        ('gender', 'gender'),
    ]

    def extra_data(self, user, uid, response, details=None, *args, **kwargs):
        data = super(EdookitOAuth2, self).extra_data(user, uid, response, details, *args, **kwargs)
        data['expires_at'] = data['expires_in'] + time.time() - 1
        return data

    def get_user_details(self, response):
        """Return user details from Edookit account"""
        tmp_user = User(first_name=response['firstname'], last_name=response['lastname'])
        return {
            'username': get_unused_username(tmp_user),
            'email': None,
            'fullname': None,
            'first_name': response['firstname'],
            'last_name': response['lastname']
        }

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        request = Request('https://oauth.edookit.net/resource/info')
        request.add_header("Authorization", "Bearer {}".format(access_token))
        response = urlopen(request)
        return json.loads(response.read().decode('utf8'))


def get_edookit_social_user(user):
    """ Get user social auth object (with edookit provider). If social user do not exists raises exception

    Args:
        user (User): django user object

    Returns:
        social user (UserSocialAuth)
    """
    if not hasattr(user, 'social_auth'):
        raise ValueError('User is not is not sign in.')
    edookit_users = user.social_auth.filter(provider='edookit')
    if len(edookit_users) == 0:
        raise ValueError('User is not paired with Edookit account.')
    if len(edookit_users) > 1:
        raise ValueError('User is associated with multiple Edookit accounts.')
    return edookit_users[0]


def refresh_token(edookit_user):
    """ Refresh access token

    Args:
        edookit_user (UserSocialAuth):

    Returns:
        extra_data (dict): extra data with new token
    """
    backend = edookit_user.get_backend_instance()
    new_data = backend.refresh_token(edookit_user.extra_data['refresh_token'])
    new_data['expires_at'] = new_data['expires_in'] + time.time() - 1
    edookit_user.extra_data.update(new_data)
    edookit_user.save()
    return edookit_user.extra_data


def get_access_token(user):
    """Get access token of user. Refreshes it if expired.

    Args:
        user (UserSocialAuth or User):

    Returns:
        access_token (str)
    """
    edookit_user = user if type(user) == UserSocialAuth else get_edookit_social_user(user)
    data = edookit_user.extra_data
    if data['expires_at'] <= time.time():
        return refresh_token(edookit_user)["access_token"]
    return data["access_token"]


def update_user_data(user):
    """Update extra data form Edookit OAuth

    Args:
        user (User): django user

    Returns:
        extra_data (dict): new updated data
    """
    edookit_user = get_edookit_social_user(user)
    backend = edookit_user.get_backend_instance()
    data = edookit_user.extra_data
    new_data = backend.user_data(access_token=get_access_token(edookit_user))
    data.update(new_data)
    edookit_user.save()
    return new_data
