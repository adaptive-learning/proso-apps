"""
Utility functions for manipulation with Python lists.
"""


import proso.dict


def flatten(xxs):
    """
    Take a list of lists and return list of values.

    .. testsetup::

        from proso.list import flatten

    .. doctest::

        >>> flatten([[1, 2], [3, 4]])
        [1, 2, 3, 4]
    """
    return [x for xs in xxs for x in xs]


def group_by(what, by):
    """
    Take a list and apply the given function on each its value, then group the
    values by the function results.

    .. testsetup::

        from proso.list import group_by

    .. doctest::

        >>> group_by([i for i in range(10)], by=lambda x: x % 2 == 0)
        {False: [1, 3, 5, 7, 9], True: [0, 2, 4, 6, 8]}

    Args:
        what: a list which will be transformed
        by: a function which will be applied on values of the given list

    Returns:
        dict: values groupped by the function results
    """
    return proso.dict.group_keys_by_values({x: by(x) for x in what})
