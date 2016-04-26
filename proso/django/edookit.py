import json
from urllib.request import urlopen, Request

from social.backends.oauth import BaseOAuth2


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

    def get_user_details(self, response):
        """Return user details from Edookit account"""
        return {
            'username': None,
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
