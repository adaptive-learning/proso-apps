from __future__ import absolute_import, unicode_literals
from django.template.loader import render_to_string
import re
from django.conf import settings
from django.utils.encoding import force_text
from django.utils import translation
from social_auth.exceptions import AuthAlreadyAssociated
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from proso.django.response import HttpError, render_json


_HTML_TYPES = ('text/html', 'application/xhtml+xml')


class ToolbarMiddleware(object):

    def process_response(self, request, response):

        if not hasattr(request, "user") or not request.user.is_staff:
            return response

        # Check for responses where the config_bar can't be inserted.
        content_encoding = response.get('Content-Encoding', '')
        content_type = response.get('Content-Type', '').split(';')[0]
        if any((getattr(response, 'streaming', False), 'gzip' in content_encoding, content_type not in _HTML_TYPES)):
            return response

        # Insert the toolbar in the response.
        content = force_text(response.content, encoding=settings.DEFAULT_CHARSET)
        insert_before = '</html>'
        pattern = re.escape(insert_before)
        response.content = re.sub(
            pattern,
            render_to_string('common_toolbar.html') + insert_before,
            content,
            flags=re.IGNORECASE)
        if response.get('Content-Length', None):
            response['Content-Length'] = len(response.content)
        return response


class ErrorMiddleware(object):

    def process_exception(self, request, exception):
        if isinstance(exception, HttpError):
            return render_json(request, {
                'error': str(exception),
                'error_type': 'bad_request'
                }, template='common_json.html', status=exception.http_status)


class AuthAlreadyAssociatedMiddleware(object):

    def process_exception(self, request, exception):
        if isinstance(exception, AuthAlreadyAssociated):
            url = request.path  # should be something like '/complete/google/'
            url = url.replace("complete", "login")
            logout(request)
            return redirect(url)


class LanguageInPathMiddleware(object):
    def __init__(self):
        self.language_codes = set(dict(settings.LANGUAGES).keys())

    def process_request(self, request):
        language_code = request.path_info.lstrip('/').split('/', 1)[0]
        if language_code in self.language_codes:
            translation.activate(language_code)
            request.LANGUAGE_CODE = translation.get_language()
            request.COOKIES[settings.LANGUAGE_COOKIE_NAME] = language_code
            request.session['django_language'] = language_code
            url = request.path
            url = url.replace('/' + language_code, '')
            return HttpResponseRedirect(url)
