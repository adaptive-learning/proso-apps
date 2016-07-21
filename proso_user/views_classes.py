from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import HttpResponseBadRequest
from django.utils.translation import ugettext as _
from proso.django.auth import get_unused_username
from proso.django.request import json_body
from proso.django.response import render_json, render
from proso_common.models import get_config
from proso_user.models import Class
from proso_user.views import profile


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
        return render_json(request, cls.to_json(), template='classes_create.html', status=201)
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
        return render_json(request, cls.to_json(), template='classes_join.html', status=200)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


def create_student(request):
    """ Create new user in class

    POST parameters (JSON):
        class:
            id of the class
        username (optional):
            username of student, if not provided username is create based on name
        password (optional):
            password of student
        first_name:
            first_name of student
        last_name (optional):
            last_name of student
        email (optional):
           e-mail of student
    """

    if not get_config('proso_user', 'allow_create_students', default=False):
        return render_json(request, {
            'error': _('Creation of new users is not allowed.'),
            'error_type': 'student_creation_not_allowed'
        }, template='class_create_student.html', help_text=create_student.__doc__, status=403)

    if request.method == 'GET':
        return render(request, 'class_create_student.html', {}, help_text=create_student.__doc__)
    if request.method == 'POST':
        if not request.user.is_authenticated() or not hasattr(request.user, "userprofile"):
            return render_json(request, {
                'error': _('User is not logged in.'),
                'error_type': 'user_unauthorized'
            }, template='class_create_student.html', status=401)
        data = json_body(request.body.decode("utf-8"))
        try:
            cls = Class.objects.get(pk=data['class'], owner=request.user.userprofile)
        except (Class.DoesNotExist, KeyError):
            return render_json(request, {
                'error': _('Class with given id not found.'),
                'error_type': 'class_not_found',
            }, template='class_create_student.html', status=404)

        if 'first_name' not in data or not data['first_name']:
            return render_json(request, {
                'error': _('First name code is missing.'),
                'error_type': 'missing_first_name'
            }, template='class_create_student.html', status=400)

        user = User(first_name=data['first_name'])
        if data.get('last_name'):
            user.last_name = data['last_name']
        if data.get('email'):
            if User.objects.filter(email=data['email']).exists():
                return render_json(request, {
                    'error': _('There is already a user with the given e-mail.'),
                    'error_type': 'email_exists'
                }, template='class_create_student.html', status=400)
            user.email = data['email']
        if data.get('username'):
            if User.objects.filter(username=data['username']).exists():
                return render_json(request, {
                    'error': _('There is already a user with the given username.'),
                    'error_type': 'username_exists'
                }, template='class_create_student.html', status=400)
            user.username = data['username']
        else:
            user.username = get_unused_username(user)
        if data.get('password'):
            user.set_password(data['password'])

        user.save()
        cls.members.add(user.userprofile)

        return render_json(request, user.userprofile.to_json(nested=True), template='class_create_student.html', status=201)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


def login_student(request):
    """
    Log in student

    POST parameters (JSON):
        student:
            profile id of the student
    """
    if not get_config('proso_user', 'allow_login_students', default=False):
        return render_json(request, {
            'error': _('Log in as student is not allowed.'),
            'error_type': 'login_student_not_allowed'
        }, template='class_create_student.html', help_text=login_student.__doc__, status=403)

    if request.method == 'GET':
        return render(request, 'class_login_student.html', {}, help_text=login_student.__doc__)
    elif request.method == 'POST':
        if not request.user.is_authenticated() or not hasattr(request.user, "userprofile"):
            return render_json(request, {
                'error': _('User is not logged in.'),
                'error_type': 'user_unauthorized'
            }, template='class_create_student.html', status=401)
        data = json_body(request.body.decode("utf-8"))
        try:
            student = User.objects.get(userprofile=data.get('student'),
                                       userprofile__classes__owner=request.user.userprofile)
        except User.DoesNotExist:
            return render_json(request, {
                'error': _('Student not found'),
                'error_type': 'student_not_found'
            }, template='class_login_student.html', status=401)
        if not student.is_active:
            return render_json(request, {
                'error': _('The account has not been activated.'),
                'error_type': 'account_not_activated'
            }, template='class_login_student.html', status=401)
        student.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, student)
        request.method = "GET"
        return profile(request)
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))
