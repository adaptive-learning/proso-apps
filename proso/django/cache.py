from django.core.cache.backends.locmem import LocMemCache
from django.views.decorators.cache import cache_page
from functools import wraps
from threading import currentThread
from django.conf import settings


_request_cache = {}
_installed_middleware = False


def cache_page_conditional(condition, timeout=3600):
    def _cache_page_conditional(viewfunc):
        @wraps(viewfunc)
        def __cache_page_conditional(request, *args, **kwargs):
            f = viewfunc
            if condition(request):
                f = cache_page(timeout)(f)
            return f(request, *args, **kwargs)
        return __cache_page_conditional
    return _cache_page_conditional


def is_cache_prepared():
    return _installed_middleware


def get_request_cache():
    assert _installed_middleware, 'RequestCacheMiddleware not loaded'
    return _request_cache[currentThread()]


class RequestCache(LocMemCache):
    def __init__(self):
        name = 'locmemcache@%i' % hash(currentThread())
        params = dict()
        super(RequestCache, self).__init__(name, params)


class RequestCacheMiddleware(object):

        def __init__(self):
            if hasattr(settings, 'TESTING') and settings.TESTING:
                return
            global _installed_middleware
            _installed_middleware = True

        def process_request(self, request):
            if _installed_middleware:
                cache = _request_cache.get(currentThread()) or RequestCache()
                _request_cache[currentThread()] = cache
                cache.clear()
