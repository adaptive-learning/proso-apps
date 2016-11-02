from django.conf import settings
from django.core.cache import cache
from django.core.cache.backends.locmem import LocMemCache
from django.views.decorators.cache import cache_page
from functools import wraps
from proso.django.config import get_config
from proso.time import timer
from threading import currentThread
import hashlib
import logging
import re


LOGGER = logging.getLogger('django.request')
CACHE_MISS = 'proso-apps-cache-miss'


_request_cache = {}
_request_permanent_cache = {}
_installed_middleware = False


def cache_page_conditional(condition, timeout=3600, cache=None):
    def _cache_page_conditional(viewfunc):
        @wraps(viewfunc)
        def __cache_page_conditional(request, *args, **kwargs):
            f = viewfunc
            if condition(request, args, kwargs):
                f = cache_page(timeout, cache=cache)(f)
            return f(request, *args, **kwargs)
        return __cache_page_conditional
    return _cache_page_conditional


class cache_pure:

    def __init__(self, expiration=60 * 60 * 24 * 30, request_only=False):
        self._expiration = expiration
        self._request_only = request_only

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            if hasattr(settings, 'TESTING') and settings.TESTING:
                return func(*args, **kwargs)
            if len(args) > 0 and re.match(r"<.+ object at \w+>", repr(args[0])) is not None:
                key_args = [args[0].__class__] + list(args[1:])
            else:
                key_args = args

            key = "{}:args:{}-kwargs:{}".format(func.__name__, repr(key_args), repr(kwargs))
            hash_key = hashlib.sha1(key.encode()).hexdigest()
            if is_cache_prepared():
                value = get_request_cache().get(hash_key, CACHE_MISS)
                if value != CACHE_MISS:
                    return value

            value = cache.get(hash_key, CACHE_MISS)
            if value != CACHE_MISS:
                return value

            timer(hash_key)
            value = func(*args, **kwargs)
            if not self._request_only:
                cache.set(hash_key, value, self._expiration)
            if is_cache_prepared():
                get_request_cache().set(hash_key, value)

            return value

        return wrapper


def get_from_request_permenent_cache(key):
    return _request_permanent_cache[currentThread()].get(key)


def set_to_request_permanent_cache(key, value):
    _request_permanent_cache[currentThread()][key] = value


def is_cache_prepared():
    return _installed_middleware


def get_request_cache():
    assert _installed_middleware, 'RequestCacheMiddleware not loaded'
    return _request_cache[currentThread()]


class RequestCache(LocMemCache):
    def __init__(self):
        name = 'locmemcache@%i' % hash(currentThread())
        params = {'max_entries': get_config('proso_common', 'request_cache.max_entries', 100000)}
        super(RequestCache, self).__init__(name, params)


class RequestCacheMiddleware(object):

        def __init__(self):
            global _installed_middleware
            _installed_middleware = True

        def process_request(self, request):
            if _installed_middleware:
                cache = _request_cache.get(currentThread()) or RequestCache()
                _request_cache[currentThread()] = cache
                _request_permanent_cache[currentThread()] = {}
                cache.clear()
