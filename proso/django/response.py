# -*- coding: utf-8 -*-
from django.http import HttpResponse
from django.shortcuts import render as original_render, redirect
from proso.django.enrichment import enrich_json_objects_by_object_type
from time import time
import json as simplejson
import logging
import markdown
import proso.django.log
import proso.release


LOGGER = logging.getLogger('django.request')


def redirect_pass_get(request, view, *args, **kwargs):
    response = redirect(view, *args, **kwargs)
    response['location'] = pass_get_parameters(request, response['location'])
    return response


def pass_get_parameters_string(request, ignore=None):
    ignore = [] if ignore is None else ignore
    to_pass = [k_v for k_v in list(request.GET.items()) if k_v[0] not in ignore]
    return '&'.join(['%s=%s' % (key_value[0], key_value[1]) for key_value in to_pass])


def append_get_parameters(dest_url, get_parameters_string):
    prefix = '&' if dest_url.find('?') != -1 else '?'
    return dest_url + prefix + get_parameters_string


def pass_get_parameters(request, dest_url, ignore=None):
    return append_get_parameters(dest_url, pass_get_parameters_string(request, ignore))


def render(request, template, data, *args, **kwargs):
    help_text = None
    if 'help_text' in kwargs:
        help_text = kwargs['help_text']
        del kwargs['help_text']
    if help_text is not None:
        help_text = markdown.markdown(help_text)
    if help_text is not None or 'help_text' not in data:
        data['help_text'] = help_text
    return original_render(request, template, data, *args, **kwargs)


def render_json(request, json, template=None, status=None, help_text=None, version=proso.release.VERSION):
    time_start = time()
    json = enrich_json_objects_by_object_type(request, json)
    if status is None or status // 100 == 2:
        json = {'data': json, 'version': version}
    if 'error' in json and 'error_type' in json:
        LOGGER.warning('%s: %s', json['error_type'], json['error'])
    if 'debug' in request.GET and request.user.is_staff and proso.django.log.is_log_prepared():
        json['debug_log'] = proso.django.log.get_request_log()
    if 'html' in request.GET:
        if help_text is not None:
            help_text = markdown.markdown(help_text)
        result = render(request, template, {'json': json, 'help_text': help_text}, status=status)
    else:
        result = JsonResponse(json, status=status)
    LOGGER.debug("rendering JSON response in %s seconds", (time() - time_start))
    return result


class HttpError(Exception):

    def __init__(self, status, message, error_type):
        super(HttpError, self).__init__(message)
        self.http_status = status
        self.error_type = error_type


class BadRequestException(HttpError):

    def __init__(self, message, error_type=None):
        super(BadRequestException, self).__init__(400, message, error_type)


class JsonResponse(HttpResponse):

    """
        JSON response
    """

    def __init__(self, content, status=None, content_type='application/json'):
        super(JsonResponse, self).__init__(
            content=simplejson.dumps(content),
            status=status,
            content_type=content_type,
        )
