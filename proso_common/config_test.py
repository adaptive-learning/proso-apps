#  -*- coding: utf-8 -*-
from proso.django.config import get_config, get_default_config_name, instantiate_from_config, set_default_config_name
import django.test


class ConfigTest(django.test.TestCase):

    def setUp(self):
        set_default_config_name('default')

    def test_get_config(self):
        self.assertEqual(get_config('proso_tests', 'a.b.c'), 'blah')
        self.assertEqual(get_config('proso_tests', 'unknown', default='is here'), 'is here')
        with self.assertRaises(Exception):
            get_config('proso_tests', 'unknown', require=True)

    def test_config_default_name(self):
        set_default_config_name('super')
        self.assertEqual(get_default_config_name(), 'super')
        self.assertIsNone(get_config('proso_tests', 'a.b.c'))

    def test_instantiate_from_config(self):
        test_instance = instantiate_from_config('proso_tests', 'instantiate_ok.inner')
        self.assertIsNotNone(test_instance)
        self.assertEqual(test_instance.dummy, 'ok')
        with self.assertRaises(Exception):
            instantiate_from_config('proso_tests', 'instantiate')
        test_instance = instantiate_from_config(
            'proso_tests', 'unknown',
            default_class='proso_common.config_test.TestClass',
            default_parameters={'dummy': 'ok'})
        self.assertIsNotNone(test_instance)
        self.assertEqual(test_instance.dummy, 'ok')


class TestClass:

    def __init__(self, dummy):
        self.dummy = dummy
