import unittest
from proso.reflection import instantiate_with_lazy_parameters


class ReflectionTest(unittest.TestCase):

    def test_instantiate_with_lazy_parameters(self):
        enable_b = False
        args = {'a': 1, 'b': False}

        def _args(arg, default=None):
            if arg == 'b' and not enable_b:
                return default
            return args.get(arg, default)

        lazy = instantiate_with_lazy_parameters('proso.test_reflection.Lazy', _args, d=100)
        self.assertEqual(lazy.a, 1)
        self.assertTrue(lazy.b)
        self.assertFalse(lazy.c)
        self.assertEqual(lazy.d, 100)
        enable_b = True
        self.assertFalse(lazy.b)
        args['a'] = 2
        self.assertEqual(lazy.a, 2)


class Lazy:

    def __init__(self, a, b=True, c=False, d=42):
        self._a = a
        self._b = b
        self._c = c
        self._d = d

    @property
    def a(self):
        return self._a()

    @property
    def b(self):
        return self._b()

    @property
    def c(self):
        return self._c()

    @property
    def d(self):
        return self._d()
