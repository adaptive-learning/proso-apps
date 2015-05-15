from functools import wraps
import hashlib
import logging
from django.core.cache import cache

LOGGER = logging.getLogger('django.request')

def disable_for_loaddata(signal_handler):
    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        if kwargs.get('raw'):
            return
        signal_handler(*args, **kwargs)
    return wrapper


def cache_pure(f, expiration=60*60*24*30):
    """ Cache decorator for functions taking one or more arguments. """
    @wraps(f)
    def wrapper(*args, **kwargs):
        print args
        key = "{}:args:{}-kwargs:{}".format(f.__name__, repr(args), repr(kwargs))
        hash = hashlib.sha1(key).hexdigest()
        if hash in cache:
            value = cache.get(hash)
            LOGGER.debug("loaded function result (%s) form CACHE; key: %s, hash %s", value, key, hash)
            return value

        print key, args

        value = f(*args, **kwargs)
        LOGGER.debug("saved function result (%s) to CACHE; key: %s, hash %s", value, key, hash)
        cache.set(hash, value, expiration)

        return value

    return wrapper
