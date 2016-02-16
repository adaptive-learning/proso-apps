def fixed_point(is_zero, plus, minus, f, x):
    """
    Get the least fixed point when it can be computed piecewise.

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
    Memoized Y combinator. Example of usage:

        @memo_Y
        def fib(f):
            def inner_fib(n):
                if n > 1:
                    return f(n - 1) + f(n - 2)
                else:
                    return n
            return inner_fib
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
