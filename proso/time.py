from functools import wraps
from proso.func import function_name
import inspect
import logging
import time
import uuid


LOGGER = logging.getLogger('django.request')
TIMERS = {}


def timer(name):
    now = time.time()
    diff = None
    if name in TIMERS:
        diff = now - TIMERS[name]
    TIMERS[name] = now
    return diff


class timeit:

    def __init__(self, name=None):
        if name is None:
            name = 'unknown'
        self._name = name
        self._id = str(uuid.uuid1())

    def __call__(self, function):

        @wraps(function)
        def timed(*args, **kw):
            ts = time.time()
            result = function(*args, **kw)
            te = time.time()
            current_frame = inspect.currentframe()
            call_frame = inspect.getouterframes(current_frame, 3)
            LOGGER.debug('[TIMEIT] .../%s:%s -> %r took %2.2f seconds' % ('/'.join(call_frame[1][1].split('/')[-2:]), call_frame[1][2], function_name(function), te - ts))
            return result

        return timed

    def __enter__(self):
        current_frame = inspect.currentframe()
        self._call_frame = inspect.getouterframes(current_frame, 2)
        timer(self._id)

    def __exit__(self, exc_type, exc_value, traceback):
        LOGGER.debug('[TIMEIT] .../%s:%s -> %r took %2.2f seconds' % ('/'.join(self._call_frame[1][1].split('/')[-2:]), self._call_frame[1][2], self._name, timer(self._id)))
