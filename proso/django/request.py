from django.conf import settings
from threading import currentThread
import datetime
import importlib
import json as simplejson
import re
import urllib


def load_query_json(query_dict, key, default_json=None):
    value = query_dict.get(key, default_json)
    try:
        return simplejson.loads(value)
    except ValueError:
        return simplejson.loads(urllib.unquote(value))


def json_body(body):
    try:
        return simplejson.loads(body)
    except ValueError:
        return parse_common_body_to_json(body)


def parse_common_body_to_json(body):
    body = body.replace('%5B', '[').replace('%5D', ']')
    result = {}
    pairs = map(lambda x: x[0], re.findall(r'(.*?[^\\])(\&|$)', body))
    for pair in pairs:
        key, value = pair.split('=')
        result = _store_body_value(key, value, result)
    return result


def _store_body_value(key_string, value, result):
    if value.isdigit():
        value = int(value)
    keys = map(lambda x: x.strip(']'), re.split('\[', key_string))
    old = result
    for i in range(len(keys)):
        k = keys[i]
        if k.isdigit():
            k = int(k)
        if isinstance(old, dict):
            new = old.get(k)
        elif k <= len(old) - 1:
            new = old[k]
        else:
            new = None
        if new is None:
            if i == len(keys) - 1:
                new = value
            else:
                if keys[i+1] == '0':
                    new = []
                else:
                    new = {}
            if isinstance(k, int):
                old.append(new)
            else:
                old[k] = new
        else:
            if i == len(keys) - 1:
                if not isinstance(new, list):
                    new = [new]
                    old[k] = new
                new.append(value)
        old = new
    return result


def is_user_id_overridden(request):
    return 'user' in request.GET and request.user.is_staff


def get_user_id(request):
    if is_user_id_overridden(request):
        return int(request.GET['user'])
    else:
        return request.user.id


def is_time_overridden(request):
    return 'time' in request.GET


def get_time(request):
    if 'time' in request.GET:
        time = datetime.datetime.strptime(request.GET['time'], '%Y-%m-%d_%H:%M:%S')
        return time
    else:
        return datetime.datetime.now()


###############################################################################
# currect request
###############################################################################

_request_initialized = False
_current_request = {}


class RequestMiddleware:
    def process_request(self, request):
        global _request_initialized
        _request_initialized = True
        _current_request[currentThread()] = request


def get_current_request(force=True):
    if not force and not _request_initialized:
        return None
    assert _request_initialized, 'RequestMiddleware is not loaded'
    return _current_request[currentThread()]
