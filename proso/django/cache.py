from django.core.cache.backends.locmem import LocMemCache
from django.views.decorators.cache import cache_page
from functools import wraps
from proso.django.config import get_config
from threading import currentThread
import logging


LOGGER = logging.getLogger('django.request')


_request_cache = {}
_request_permanent_cache = {}
_installed_middleware = False


def cache_page_conditional(condition, timeout=3600):
    def _cache_page_conditional(viewfunc):
        @wraps(viewfunc)
        def __cache_page_conditional(request, *args, **kwargs):
            f = viewfunc
            if condition(request, args, kwargs):
                LOGGER.debug('cache hit for view function {}'.format(f.__name__))
                f = cache_page(timeout)(f)
            return f(request, *args, **kwargs)
        return __cache_page_conditional
    return _cache_page_conditional


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
