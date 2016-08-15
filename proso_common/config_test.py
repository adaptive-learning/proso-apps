from .models import instantiate_from_config, get_config, reset_custom_configs, reset_custom_config_filters, CustomConfig, add_custom_config_filter
from proso.django.config import get_default_config_name, set_default_config_name
from proso.django.request import set_current_request
from django.contrib.auth.models import User
import django.test


class ConfigTest(django.test.TestCase):

    def setUp(self):
        set_default_config_name('default')
        reset_custom_configs()
        reset_custom_config_filters()
        self.user = User.objects.create_user(
            username='test', email='test@test.com', password='top_secret'
        )
        request = django.test.RequestFactory().get('/common/config')
        request.user = self.user
        set_current_request(request)
        CustomConfig.objects.all().delete()

    def test_custom_configs(self):
        CustomConfig.objects.try_create('proso_tests', 'a.b.c', 'blah_overriden', self.user.id)
        self.assertEqual(get_config('proso_tests', 'a.b.c'), 'blah_overriden')
        CustomConfig.objects.try_create('proso_tests', 'a.b.c', 'blah_overriden_second', self.user.id, 'test_condition', 'value')
        self.assertEqual(get_config('proso_tests', 'a.b.c'), 'blah_overriden')
        add_custom_config_filter(test_filter)
        self.assertEqual(get_config('proso_tests', 'a.b.c'), 'blah_overriden_second')

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


def test_filter(key, value):
    return key == 'test_condition'
