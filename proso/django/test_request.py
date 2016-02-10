# -*- coding: utf-8 -*-
import unittest
import proso.django.request as request


class TestParseCommonBodyToJson(unittest.TestCase):

    def test_simple(self):
        self.assertEqual(
            {'x': 1, 'y': 2},
            request.parse_common_body_to_json('x=1&y=2')
        )
        self.assertEqual(
            {'x': {'a': 1, 'b': 2}, 'y': 2},
            request.parse_common_body_to_json('x[a]=1&x[b]=2&y=2')
        )

    def test_list(self):
        self.assertEqual(
            {'x': [1, 2, 3]},
            request.parse_common_body_to_json('x=1&x=2&x=3')
        )
        self.assertEqual(
            {'x': {'y': [1, 2]}},
            request.parse_common_body_to_json('x[y][0]=1&x[y][1]=2')
        )
        self.assertEqual(
            {'x': [{'y': 1}, {'y': 2}]},
            request.parse_common_body_to_json('x[0][y]=1&x[1][y]=2')
        )
