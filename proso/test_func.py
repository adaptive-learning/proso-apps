# -*- coding: utf-8 -*-
import unittest
from proso.func import memo_Y, fixed_point


class TestFixedPoints(unittest.TestCase):

    def test_memo_Y(self):
        @memo_Y
        def fib(f):
            def inner_fib(n):
                if n > 1:
                    return f(n - 1) + f(n - 2)
                else:
                    return n
            return inner_fib

        self.assertEqual(fib(100), 354224848179261915075)

    def test_fixed_point(self):
        self.assertEqual(sorted(fixed_point(
            lambda xs: len(xs) == 0,
            lambda xs, ys: xs + ys,
            lambda xs, ys: [x for x in xs if x not in ys],
            lambda xs: [x + 1 for x in xs if x < 100],
            [0, 5, 8]
        )), list(range(101)))
