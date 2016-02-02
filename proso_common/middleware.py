
from django.template.loader import render_to_string
import re
from django.conf import settings
from django.utils.encoding import force_text
from django.utils import translation
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from social.exceptions import AuthAlreadyAssociated
from proso.django.response import HttpError, render_json
import datetime
import logging

LOGGER = logging.getLogger('django.request')
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
            request.session[translation.LANGUAGE_SESSION_KEY] = language_code
            url = request.path
            url = url.replace('/' + language_code, '')
            return HttpResponseRedirect(url)


def redirect_domain(request, target_domain):
    sessionid = request.COOKIES.get('sessionid', '')
    url = 'http://' + target_domain + request.get_full_path()
    if sessionid != '':
        url += '?sessionid=' + sessionid
    return redirect(url, permanent=True)


def set_lang(request, language_code):
    translation.activate(language_code)
    request.LANGUAGE_CODE = translation.get_language()
    request.COOKIES[settings.LANGUAGE_COOKIE_NAME] = language_code
    request.session[translation.LANGUAGE_SESSION_KEY] = language_code


class LanguageInDomainMiddleware(object):
    def __init__(self):
        self.language_codes = set(dict(settings.LANGUAGES).keys())

    def process_request(self, request):
        language_code = translation.get_language()
        target_domain = settings.LANGUAGE_DOMAINS[language_code]
        if target_domain != request.META['HTTP_HOST']:
            domain_to_lang_dict = dict((v, k) for k, v in settings.LANGUAGE_DOMAINS.items())
            language_code = domain_to_lang_dict.get(request.META['HTTP_HOST'])
            if language_code is not None:
                set_lang(request, language_code)
            else:
                LOGGER.error(
                    'LanguageInDomainMiddleware: invalid HTTP_HOST: {}'.format(
                        request.META['HTTP_HOST']))

        language_code = request.path_info.lstrip('/').split('/', 1)[0]
        if language_code in self.language_codes:
            target_domain = settings.LANGUAGE_DOMAINS[language_code]
            if target_domain != request.META['HTTP_HOST']:
                return redirect_domain(request, target_domain)
            if request.COOKIES.get('sessionid', 'None') == request.GET.get('sessionid', ''):
                # TODO: remove get param
                pass
            set_lang(request, language_code)
            url = request.get_full_path()
            url = url.replace('/' + language_code, '')
            return HttpResponseRedirect(url)

    def process_response(self, request, response):
        if request.method == 'GET' and 'sessionid' in request.GET:
            max_age = 7 * 24 * 60 * 60
            expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=max_age)
            response.set_cookie('sessionid', request.GET['sessionid'], expires=expires)
        return response


class GoogleAuthChangeDomain(object):
    def process_request(self, request):
        if request.path_info == '/login/google-oauth2/':
            auth_domain = settings.AUTH_DOMAIN
            if auth_domain != request.META['HTTP_HOST']:
                return redirect_domain(request, auth_domain)
        if request.path_info == '/complete/google-oauth2/':
            language_code = translation.get_language()
            target_domain = settings.LANGUAGE_DOMAINS[language_code]
            if target_domain != request.META['HTTP_HOST']:
                return redirect_domain(request, target_domain)
