LAMBDA = lambda: 0


def is_lambda(fun):
    """
    Check whether the given function is a lambda function.

    .. testsetup::

        from proso.func import is_lambda

    .. testcode::

        def not_lambda_fun():
            return 1

        lambda_fun = lambda: 1

        print(
            is_lambda(not_lambda_fun),
            is_lambda(lambda_fun)
        )
    .. testoutput::

        False True

    Args:
        fun (function)

    Returns:
        bool: True if the given function is a lambda function, False otherwise
    """
    return isinstance(fun, type(LAMBDA)) and fun.__name__ == LAMBDA.__name__


def fixed_point(is_zero, plus, minus, f, x):
    """
    Get the least fixed point when it can be computed piecewise.

    .. testsetup::

        from proso.func import fixed_point

    .. doctest::

        >>> sorted(fixed_point(
        ...    is_zero=lambda xs: len(xs) == 0,
        ...    plus=lambda xs, ys: xs + ys,
        ...    minus=lambda xs, ys: [x for x in xs if x not in ys],
        ...    f=lambda xs: [x + 1 for x in xs if x < 10],
        ...    x=[0, 5, 8]
        ... ))
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    Args:
        is_zero: function returning True if the given value is zero
        plus: function taking two values and returning their addition
        minus: function taking two values and returning ther difference
        f: function computing the expected value
        x: initial value

    Returns:
        The least fixed point.
    """

    @memo_Y
    def _fixed_point(fixed_point_fun):
        def __fixed_point(collected, new):
            diff = minus(new, collected)
            if is_zero(diff):
                return collected
            return fixed_point_fun(plus(collected, diff), f(diff))
        return __fixed_point

    return _fixed_point(x, f(x))


def memo_Y(f):
    """
    Memoized Y combinator.

    .. testsetup::

        from proso.func import memo_Y

    .. testcode::

        @memo_Y
        def fib(f):
            def inner_fib(n):
                if n > 1:
                    return f(n - 1) + f(n - 2)
                else:
                    return n
            return inner_fib

        print(fib(100))

    .. testoutput::

        354224848179261915075
    """
    sub = {}

    def Yf(*args):
        hashable_args = tuple([repr(x) for x in args])
        if args:
            if hashable_args not in sub:
                ret = sub[hashable_args] = f(Yf)(*args)
            else:
                ret = sub[hashable_args]
            return ret
        return f(Yf)()
    return f(Yf)
