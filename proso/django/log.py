from logging import Handler
from collections import defaultdict
from threading import currentThread

_request_log = defaultdict(list)
_installed_middleware = False
_should_log = False


def is_active():
    return _should_log


def is_log_prepared():
    return _installed_middleware


def get_request_log():
    assert _installed_middleware, 'RequestLogMiddleware not loaded'
    return _request_log[currentThread()]


class RequestHandler(Handler):

    def __init__(self):
        Handler.__init__(self)

    def emit(self, record):
        if _should_log:
            self.format(record)
            get_request_log().append({
                'message': record.message,
                'pathname': record.pathname,
                'module': record.module,
                'line_number': record.lineno,
                'filename': record.filename,
                'level': record.levelname
            })


class RequestLogMiddleware(object):

    def __init__(self):
        global _installed_middleware
        _installed_middleware = True

    def process_request(self, request):
        global _should_log
        global _request_log
        _should_log = 'debug' in request.GET and request.user.is_staff
        _request_log[currentThread()] = []
