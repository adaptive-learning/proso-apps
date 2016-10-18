import importlib
import inspect
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
    return get_class(classname)(*args, **kwargs)


def instantiate_with_lazy_parameters(classname, kwarg_fun, **kwargs):
    clazz = get_class(classname)
    arg_spec = inspect.getargspec(clazz.__init__)
    args = arg_spec.args[1:]
    args_default = dict(zip(args[-len(arg_spec.defaults):], arg_spec.defaults))
    args_default.update(kwargs)

    def _kwarg_fun(arg):
        if arg not in args_default:
            return lambda: kwarg_fun(arg)
        else:
            return lambda: kwarg_fun(arg, args_default[arg])
    return clazz(**{
        arg: _kwarg_fun(arg)
        for arg in args
    })


def get_class(classname):
    matched = re.match('(.*)\.(\w+)', classname)
    if matched is None:
        raise Exception('can found only class with packages: %s' % classname)
    module = importlib.import_module(matched.groups()[0])
    return getattr(module, matched.groups()[1])
