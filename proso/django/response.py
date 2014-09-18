# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import HttpResponse
import json as simplejson
from django.conf import settings


def redirect_pass_get(request, view, *args, **kwargs):
    response = redirect(view, *args, **kwargs)
    response['location'] = pass_get_parameters(request, response['location'])
    return response


def pass_get_parameters(request, dest_url, ignore=None):
    ignore = [] if ignore is None else ignore
    to_pass = filter(lambda (k, v): k not in ignore, request.GET.items())
    if len(to_pass) == 0:
        return dest_url
    else:
        prefix = '&' if dest_url.find('?') != -1 else '?'
        return dest_url + prefix + '&'.join(map(lambda (key, value): '%s=%s' % (key, value), to_pass))


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
