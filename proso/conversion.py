import json

try:
    JSONDecodeError = json.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError


def str2type(value):
    """
    Take a string and convert it to a value of proper type.


        .. testsetup::

            from proso.coversion import str2type

        .. doctest::

            >>> print(str2type("[1, 2, 3]")
            [1, 2, 3]
    """
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except JSONDecodeError:
        return value
