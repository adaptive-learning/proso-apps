# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.context_processors import csrf
from django.shortcuts import render_to_response
from proso_questions_client.utils import StaticFiles, get_user, get_page_title, get_flatblock
from proso_questions.models import Category
from django.contrib.auth import logout
from django.http import HttpResponse
import json
from django.utils import simplejson
from logging import getLogger
from django.core.mail import send_mail

LOGGER = getLogger(__name__)


def home(request, hack=None):
    color_scheme = get_flatblock('color_scheme')
    if color_scheme != '':
        color_scheme += '-'
    JS_FILES = (
        "static/dist/js/fallbacks.min.js",
        "static/dist/js/libs.min.js",
        "static/dist/js/proso-questions-client.min.js",
    )
    CSS_FILES = (
        "static/bower_components/angular-material/angular-material.min.css",
        "static/bower_components/bootstrap/dist/css/bootstrap.min.css",
        "static/css/" + color_scheme + "app.css",
    )
    request.META["CSRF_COOKIE_USED"] = True
    hashes = dict((key, value)
                  for key, value
                  in settings.HASHES.iteritems()
                  if "/lib/" not in key and "/js/" not in key and "/sass/" not in key
                  )
    c = {
        'title': get_page_title(),
        'isProduction': settings.ON_PRODUCTION,
        'css_files': StaticFiles.add_hash(CSS_FILES),
        'js_files': StaticFiles.add_hash(JS_FILES),
        'hashes': json.dumps(hashes),
        'user': get_user(request),
        'isHomepage': hack is None,
        'categories': Category.objects.all().order_by('id'),
        'above_fold_styles': "generated/" + color_scheme + "above-fold.css",
    }
    c.update(csrf(request))
    return render_to_response('home.html', c)


def logout_view(request):
    logout(request)
    return HttpResponse('{"username":""}')


def is_likely_worthless(feedback):
    return len(feedback['text']) <= 50


def feedback(request):
    if request.body:
        feedback = simplejson.loads(request.body)
        mail_text = ('## This email is sent from the feedback form on the site. ##\n\n' +
                     feedback['text'] + '\n' +
                     '\n\n## end of user message ##\n' +
                     '\nemail: ' + feedback['email'] +
                     '\nuser_id: ' + str(request.user.id) +
                     '\nusername: ' + request.user.username +
                     '\npage: ' + feedback['page'] +
                     '\nuser agent: ' + feedback['user_agent'])
        if is_likely_worthless(feedback):
            mail_from = settings.FEEDBACK_FROM_SPAM
        else:
            mail_from = settings.FEEDBACK_FROM
        send_mail('autoskolachytre.cz feedback',
                  mail_text,
                  mail_from,
                  [settings.FEEDBACK_TO],
                  fail_silently=False)
        # raise Exception(mail_text + settings.FEEDBACK_TO)
        LOGGER.debug("email sent %s\n", mail_text)
        response = {
            'type': 'success',
            'msg': "Děkujeme Vám za zaslané informace. Feedback od uživatelů je pro nás k nezaplacení.",
        }
    return HttpResponse(json.dumps(response))
