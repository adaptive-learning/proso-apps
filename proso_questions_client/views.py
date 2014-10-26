# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.context_processors import csrf
from django.shortcuts import render_to_response
from proso_questions_client.utils import StaticFiles, get_user, get_page_title, get_flatblock
from proso_questions.models import Category
from django.contrib.auth import logout
from django.http import HttpResponse
import json


def home(request, hack=None):
    color_scheme = get_flatblock('color_scheme')
    if color_scheme != '':
        color_scheme += '-'
    JS_FILES = (
        "static/dist/js/fallbacks.min.js",
        "static/dist/js/libs.min.js",
        "static/dist/js/proso-questions-client.min.js",
        "static/lib/angular-1.2.9/i18n/angular-locale_cs.js",
    )
    CSS_FILES = (
        "static/bower_components/angular-material/angular-material.min.css",
        "static/bower_components/bootstrap/dist/css/bootstrap.css",
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
