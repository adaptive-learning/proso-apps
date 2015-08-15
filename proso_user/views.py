from django.core.exceptions import ObjectDoesNotExist
from proso.django.response import render, render_json
import django.contrib.auth as auth
from proso.django.request import get_user_id, json_body, is_user_id_overridden
from models import Session, UserProfile, TimeZone, migrate_google_openid_user
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.views.decorators.csrf import ensure_csrf_cookie
from lazysignup.decorators import allow_lazy_user
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
import json
from django.utils.translation import ugettext as _
from proso.django.config import get_config


@allow_lazy_user
def profile(request, status=200):
    """
    Get the user's profile. If the user has no assigned profile, the HTTP 404
    is returned. Make a POST request to modify the user's profile.

    GET parameters:
        html
            turn on the HTML version of the API
        username:
            username of user (only for users with public profile)
        stats:
            attache addition user statistics

    POST parameters (JSON):
        send_emails:
            switcher turning on sending e-mails to user
        public:
            swicher making the user's profile publicly available
        user:
            password:
                user's password
            password_check:
                user's password again to check it
            first_name (optional):
                user's first name
            last_name (optional):
                user's last name
    """
    if request.method == 'GET':
        if request.GET.get("username", False):
            try:
                user_profile = User.objects.get(username=request.GET.get("username"),
                                                userprofile__public=True).userprofile
            except ObjectDoesNotExist:
                raise Http404("user not found or have not public profile")
        else:
            user_id = get_user_id(request)
            if get_config('proso_user', 'google.openid.migration', default=True) and not is_user_id_overridden(request):
                migrated_user = migrate_google_openid_user(request.user)
                if migrated_user is not None:
                    auth.logout(request)
                    migrated_user.backend = 'social_auth.backends.google.GoogleOAuth2Backend'
                    auth.login(request, migrated_user)
            user_profile = get_object_or_404(UserProfile, user_id=user_id)
        return render_json(
            request, _to_json(request, user_profile, stats=request.GET.get("stats", False)), status=status,
            template='user_profile.html', help_text=profile.__doc__)
    elif request.method == 'POST':
        with transaction.atomic():
            to_save = json_body(request.body)
            user_id = get_user_id(request)
            user_profile = get_object_or_404(UserProfile, user_id=user_id)
            user = to_save.get('user', None)
            if 'send_emails' in to_save:
                user_profile.send_emails = bool(to_save['send_emails'])
            if 'public' in to_save:
                user_profile.public = bool(to_save['public'])
            if user:
                error = _save_user(request, user, new=False)
                if error:
                    return render_json(request, error, template='user_json.html', status=400)
            user_profile.save()
        request.method = "GET"
        return profile(request, status=202)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


@ensure_csrf_cookie
def login(request):
    """
    Log in

    GET parameters:
        html
            turn on the HTML version of the API

    POST parameters (JSON):
        username:
            user's name
        password:
            user's password
    """
    if request.method == 'GET':
        return render(request, 'user_login.html', {}, help_text=login.__doc__)
    elif request.method == 'POST':
        credentials = json_body(request.body)
        user = auth.authenticate(
            username=credentials.get('username', ''),
            password=credentials.get('password', ''),
        )
        if user is None:
            return render_json(request, {
                'error': _('Password or username does not match.'),
                'error_type': 'password_username_not_match'
            }, template='user_json.html', status=401)
        if not user.is_active:
            return render_json(request, {
                'error': _('The account has not been activated.'),
                'error_type': 'account_not_activated'
            }, template='user_json.html', status=401)
        auth.login(request, user)
        request.method = "GET"
        return profile(request)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


def logout(request):
    auth.logout(request)
    return HttpResponse('ok', status=202)


@allow_lazy_user
@transaction.atomic
def signup(request):
    """
    Create a new user with the given credentials.

    GET parameters:
        html
            turn on the HTML version of the API

    POST parameters (JSON):
        username:
            user's name
        email:
            user's e-mail
        password:
            user's password
        password_check:
            user's password again to check it
        first_name (optional):
            user's first name
        last_name (optional):
            user's last name
    """
    if request.method == 'GET':
        return render(request, 'user_signup.html', {}, help_text=signup.__doc__)
    elif request.method == 'POST':
        if request.user.is_authenticated() and hasattr(request.user, "userprofile"):
            return render_json(request, {
                'error': _('User already logged in'),
                'error_type': 'username_logged'
            }, template='user_json.html', status=400)
        credentials = json_body(request.body)
        error = _save_user(request, credentials, new=True)
        if error is not None:
            return render_json(request, error, template='user_json.html', status=400)
        else:
            auth.login(request, request.user)
            request.method = "GET"
            return profile(request, status=201)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


@ensure_csrf_cookie
@allow_lazy_user
@transaction.atomic
def session(request):
    """
    Get the information about the current session or modify the current session.

    GET parameters:
      html
        turn on the HTML version of the API

    POST parameters:
      locale:
        client's locale
      time_zone:
        client's time zone
      display_width:
        width of the client's display
      display_height
        height of the client's display
    """

    if request.user.id is None:  # Google Bot
        return render_json(request, {
            'error': _('There is no user available to create a session.'),
            'error_type': 'user_undefined'
        }, status=400, template='user_json.html')

    if request.method == 'GET':
        return render_json(
            request,
            _to_json(request, Session.objects.get_current_session()),
            template='user_session.html', help_text=session.__doc__)
    elif request.method == 'POST':
        current_session = Session.objects.get_current_session()
        if current_session is None:
            return HttpResponseBadRequest("there is no current session to modify")
        data = json_body(request.body)
        locale = data.get('locale', None)
        time_zone = data.get('time_zone', None)
        display_width = data.get('display_width', None)
        display_height = data.get('display_height', None)
        if locale:
            current_session.locale = locale
        if time_zone:
            current_session.time_zone = TimeZone.objects.from_content(time_zone)
        if display_width:
            current_session.display_width = display_width
        if display_height:
            current_session.display_height = display_height
        current_session.save()
        return HttpResponse('ok', status=202)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


def initmobile_view(request):
    """
    Create lazy user with a password. Used from the Android app.
    Also returns csrf token.

    GET parameters:
        username:
            user's name
        password:
            user's password
    """
    if 'username' in request.GET and 'password' in request.GET:
        username = request.GET['username']
        password = request.GET['password']
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
    else:
        user = request.user
    response = {
        'username': user.username,
        'csrftoken': get_token(request),
    }
    if not user.has_usable_password():
        password = User.objects.make_random_password()
        user.set_password(password)
        user.save()
        response['password'] = password
    return HttpResponse(json.dumps(response))


def _to_json(request, value, **kwargs):
    if isinstance(value, list):
        json = map(lambda x: x if isinstance(x, dict) else x.to_json(**kwargs), value)
    elif not isinstance(value, dict):
        json = value.to_json(**kwargs)
    else:
        json = value
    return json


def _check_credentials(credentials, new=False):
    if new and not credentials.get('username'):
        return {
            'error': _('There is no username'),
            'error_type': 'username_empty'
        }
    if new and not credentials.get('email'):
        return {
            'error': _('There is no e-mail'),
            'error_type': 'email_empty'
        }
    if new and not credentials.get('password'):
        return {
            'error': _('There is no password'),
            'error_type': 'password_empty'
        }

    if credentials.get('password') and credentials['password'] != credentials.get('password_check'):
        return {
            'error': _('Passwords do not match.'),
            'error_type': 'password_not_match'
        }
    if credentials.get('username') and _user_exists(username=credentials['username']):
        return {
            'error': _('There is already a user with the given username.'),
            'error_type': 'username_exists'
        }
    if new and _user_exists(email=credentials['email']):
        return {
            'error': _('There is already a user with the given e-mail.'),
            'error_type': 'email_exists'
        }
    return None


def _save_user(request, credentials, new=False):
    error = _check_credentials(credentials, new)
    if error is not None:
        return error
    else:
        user = request.user
        if new:
            user.username = credentials['username']
            user.email = credentials['email']
        if credentials.get('password'):
            user.set_password(credentials['password'])
        if credentials.get('first_name'):
            user.first_name = credentials['first_name']
        if credentials.get('last_name'):
            user.last_name = credentials['last_name']
        user.save()
        return None


def _user_exists(**kwargs):
    return User.objects.filter(**kwargs).exists()


@ensure_csrf_cookie
def user_service(request):
    if not hasattr(request.user, "userprofile"):
        user = ""
    else:
        user = json.dumps(request.user.userprofile.to_json())
    return render(request, "user_service.html", {"user": user})
