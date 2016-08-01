import importlib
import re


def instantiate(classname, *args, **kwargs):
    """
    Take a classname and instantiate it.

    .. testsetup::

        from proso.reflection import instantiate

    .. doctest::

        >>> instantiate('collections.defaultdict')
        defaultdict(None, {})
    """
    matched = re.match('(.*)\.(\w+)', classname)
    if matched is None:
        raise Exception('can instantiate only class with packages: %s' % classname)
    module = importlib.import_module(matched.groups()[0])
    return getattr(module, matched.groups()[1])(*args, **kwargs)
