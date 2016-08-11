from functools import wraps
import logging
import time


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

    def __call__(self, function):

        @wraps(function)
        def timed(*args, **kw):
            ts = time.time()
            result = function(*args, **kw)
            te = time.time()
            LOGGER.debug('%s: %r took %2.2f seconds' % (self._name, function.__name__, te - ts))
            return result

        return timed
