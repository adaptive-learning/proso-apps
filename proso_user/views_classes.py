from django.http import HttpResponse, HttpResponseBadRequest

from proso.django.request import json_body
from proso.django.response import render_json, render
from proso_user.models import Class
from django.utils.translation import ugettext as _


def classes(request):
    """Get all classes of current user"""

    if not request.user.is_authenticated() or not hasattr(request.user, "userprofile"):
        return render_json(request, {
            'error': _('User is not logged in'),
            'error_type': 'user_unauthorized'
        }, template='user_json.html', status=401)
    clss = [c.to_json() for c in Class.objects.filter(owner=request.user.userprofile)]

    return render_json(request, clss, status=200, template='user_json.html', help_text=classes.__doc__)


def create_class(request):
    """Create new class

    POST parameters (JSON):
        name:
            Human readable name of class
        code (optional):
            unique code of class used for joining to class
    """

    if request.method == 'GET':
        return render(request, 'classes_create.html', {}, help_text=create_class.__doc__)

    if request.method == 'POST':
        if not request.user.is_authenticated() or not hasattr(request.user, "userprofile"):
            return render_json(request, {
                'error': _('User is not logged in.'),
                'error_type': 'user_unauthorized'
            }, template='classes_create.html', status=401)

        data = json_body(request.body.decode("utf-8"))
        if 'code' in data and Class.objects.filter(code=data['code']).exists():
            return render_json(request, {
                'error': _('A class with this code already exists.'),
                'error_type': 'class_with_code_exists'
            }, template='classes_create.html', status=400)

        if 'name' not in data or not data['name']:
            return render_json(request, {'error': _('Class name is missing.'), 'error_type': 'missing_class_name'},
                               template='classes_create.html', status=400)

        cls = Class(name=data['name'], owner=request.user.userprofile)
        if 'code' in data:
            cls.code = data['code']
        cls.save()
        return HttpResponse('ok', status=201)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


def join_class(request):
    """Join a class

    POST parameters (JSON):
        code:
            code of the class
    """

    if request.method == 'GET':
        return render(request, 'classes_join.html', {}, help_text=join_class.__doc__)

    if request.method == 'POST':
        if not request.user.is_authenticated() or not hasattr(request.user, "userprofile"):
            return render_json(request, {
                'error': _('User is not logged in.'),
                'error_type': 'user_unauthorized'
            }, template='classes_join.html', status=401)

        data = json_body(request.body.decode("utf-8"))

        if 'code' not in data or not data['code']:
            return render_json(request, {'error': _('Class code is missing.'), 'error_type': 'missing_class_code'},
                               template='classes_join.html', status=400)

        try:
            cls = Class.objects.get(code=data['code'])
        except Class.DoesNotExist:
            return render_json(request, {
                'error': _('Class with given code not found.'),
                'error_type': 'class_not_found',
            }, template='classes_join.html', status=404)

        cls.members.add(request.user.userprofile)
        return HttpResponse('ok', status=200)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))
