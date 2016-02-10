from logging import Handler
from collections import defaultdict
from threading import currentThread
from django.utils.log import AdminEmailHandler
import json


_request_log = defaultdict(list)
_installed_middleware = False
_should_log = defaultdict(lambda: False)


def is_active():
    return _should_log[currentThread()]


def is_log_prepared():
    return _installed_middleware


def get_request_log():
    assert _installed_middleware, 'RequestLogMiddleware not loaded'
    return _request_log[currentThread()]


class RequestHandler(Handler):

    def __init__(self):
        Handler.__init__(self)

    def emit(self, record):
        if is_active():
            self.format(record)
            get_request_log().append({
                'message': record.message,
                'pathname': record.pathname,
                'module': record.module,
                'line_number': record.lineno,
                'filename': record.filename,
                'level': record.levelname
            })


class AdminJavascriptEmailHandler(AdminEmailHandler):

    def format(self, record):
        return 'Message: %s\nUser: %s\nClient Data: %s' % (record.getMessage(), record.user, json.dumps(record.client_data, indent=4, sort_keys=True))


class RequestLogMiddleware(object):

    def __init__(self):
        global _installed_middleware
        _installed_middleware = True

    def process_request(self, request):
        global _should_log
        global _request_log
        _should_log[currentThread()] = 'debug' in request.GET and request.user.is_staff
        _request_log[currentThread()] = []
