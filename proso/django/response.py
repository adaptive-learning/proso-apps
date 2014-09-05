# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import HttpResponse
import json as simplejson
from django.conf import settings


def redirect_pass_get(request, view, *args, **kwargs):
    response = redirect(view, *args, **kwargs)
    if len(request.GET.items()) > 0:
        response['location'] += '?' + '&'.join(map(lambda (key, value): '%s=%s' % (key, value), request.GET.items()))
    return response


def render_json(request, json, template=None, status=None):
    if 'html' in request.GET:
        return render(request, template, {'json': json}, status=status)
    else:
        return JsonResponse(json, status=status)


class JsonResponse(HttpResponse):

    """
        JSON response
    """

    def __init__(self, content, mimetype='application/json',
                 status=None, content_type=None):
        indent = 4 if settings.DEBUG else None
        super(JsonResponse, self).__init__(
            content=simplejson.dumps(content, indent=indent),
            mimetype=mimetype,
            status=status,
            content_type=content_type,
        )
