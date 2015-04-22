import re
import importlib
import time

_timers = {}


def timer(name):
    now = time.clock()
    if name in _timers:
        diff = now - _timers[name]
        return diff
    _timers[name] = now


def instantiate(classname, *args, **kwargs):
    matched = re.match('(.*)\.(\w+)', classname)
    if matched is None:
        raise Exception('can instantiate only class with packages: %s' % classname)
    module = importlib.import_module(matched.groups()[0])
    return getattr(module, matched.groups()[1])(*args, **kwargs)
