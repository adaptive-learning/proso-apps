from django.core.management import call_command
from proso.django.test import TestCase
from .models import SubscriptionPlan


class TestPlansLoading(TestCase):

    def test_loading(self):
        call_command('load_subscription_plans', 'testproject/test_data/subscription/plans.json')
        first = SubscriptionPlan.objects.get(identifier='first')
        second = SubscriptionPlan.objects.get(identifier='second')
        self.assertTrue(first.active)
        self.assertFalse(second.active)
        self.assertEqual(first.descriptions.all().count(), 2)
        self.assertEqual(second.descriptions.all().count(), 2)
