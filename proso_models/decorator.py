import inspect
from functools import wraps
from proso.django.cache import get_request_cache, is_cache_prepared


class cache_environment_for_item:

    def __init__(self, default=None):
        self._default = default

    def __call__(self, func):
        decorator_self = self

        @wraps(func)
        def _wrapper(self, *args, **kwargs):
            if not func.__name__.endswith('_more_items') or _should_skip():
                return func(self, *args, **kwargs)
            args_dict = dict(zip(inspect.getargspec(func).args[1:], args) + kwargs.items())
            default = decorator_self._default
            if default is None:
                default = args_dict.get('default', None)
            items = args_dict.get('items')
            if items is None:
                raise Exception('items have to be specified')
            cached_items = {}
            other_items = []
            cache_keys = dict(zip(items, map(lambda x: _cache_key(func, x, args, kwargs), items)))
            for item in items:
                cache_key = cache_keys[item]
                if not _cache_has_key(cache_key):
                    other_items.append(item)
                else:
                    cached_items[item] = _cache_get(cache_key, default)
            if len(other_items) > 0:
                args_dict['items'] = other_items
                inner_result = dict(zip(other_items, func(self, **args_dict)))
                for item, value in inner_result.items():
                    cache_key = cache_keys[item]
                    _cache_set(cache_key, value)
            else:
                inner_result = {}
            return map(lambda item: cached_items.get(item, inner_result.get(item)), items)
        return _wrapper


def _should_skip():
    return not is_cache_prepared()


def _cache_has_key(key):
    return key in get_request_cache()


def _cache_get(key, default):
    return get_request_cache().get(key, default)


def _cache_set(key, value):
    get_request_cache().set(key, value)


def _cache_key(func, item, args, kwargs):
    funcname = func.__name__.replace('_more_items', '')
    args_dict = dict(zip(inspect.getargspec(func).args[1:], args) + kwargs.items())
    del args_dict['items']
    return '____'.join([
        str(funcname),
        str(item),
        '___'.join(map(lambda (key, value): str(key) + '_' + str(value), sorted(args_dict.items())))]
    )
