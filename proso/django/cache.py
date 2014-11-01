from functools import wraps
from django.views.decorators.cache import cache_page


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
