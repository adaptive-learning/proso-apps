from proso.django.response import render, render_json
from models import Session
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import ensure_csrf_cookie
from lazysignup.decorators import allow_lazy_user
from django.db import transaction


def home(request):
    return render(request, 'user_home.html', {})


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
    if request.method == 'GET':
        return render_json(
            request,
            _to_json(request, Session.objects.get_current_session()),
            template='user_session.html', help_text=session.__doc__)
    elif request.method == 'POST':
        current_session = Session.objects.get_current_session()
        if current_session is None:
            return HttpResponseBadRequest("there is no current session to modify")
        locale = request.POST.get('locale', None)
        time_zone = request.POST.get('time_zone', None)
        display_width = request.POST.get('display_width', None)
        display_height = request.POST.get('display_height', None)
        if locale:
            current_session.locale = locale
        if time_zone:
            current_session.time_zone = time_zone
        if display_width:
            current_session.display_width = display_width
        if display_height:
            current_session.display_height = display_height
        current_session.save()
        return HttpResponse('ok', status=202)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


def _to_json(request, value):
    if isinstance(value, list):
        json = map(lambda x: x if isinstance(x, dict) else x.to_json(), value)
    elif not isinstance(value, dict):
        json = value.to_json()
    else:
        json = value
    return json
