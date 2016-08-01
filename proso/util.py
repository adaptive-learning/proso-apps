import importlib
import logging
import re
import time
from functools import wraps


LOGGER = logging.getLogger('django.request')


_timers = {}


def timer(name):
    now = time.time()
    diff = None
    if name in _timers:
        diff = now - _timers[name]
    _timers[name] = now
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

            LOGGER.debug('%s: %r (%r, %r) took %2.2f seconds' % (self._name, function.__name__, args, kw, te - ts))
            return result

        return timed


def instantiate(classname, *args, **kwargs):
    matched = re.match('(.*)\.(\w+)', classname)
    if matched is None:
        raise Exception('can instantiate only class with packages: %s' % classname)
    module = importlib.import_module(matched.groups()[0])
    return getattr(module, matched.groups()[1])(*args, **kwargs)
