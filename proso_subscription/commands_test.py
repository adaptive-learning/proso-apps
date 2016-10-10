from django.core.management import call_command
from proso.django.test import TestCase
from .models import SubscriptionPlan, DiscountCode


class TestPlansLoading(TestCase):

    def test_loading(self):
        call_command('load_subscription_plans', 'testproject/test_data/subscription/plans.json')
        first = SubscriptionPlan.objects.get(identifier='first')
        second = SubscriptionPlan.objects.get(identifier='second')
        self.assertTrue(first.active)
        self.assertFalse(second.active)
        self.assertEqual(first.descriptions.all().count(), 2)
        self.assertEqual(second.descriptions.all().count(), 2)
        self.assertTrue(first.featured)
        code_global = DiscountCode.objects.get(identifier="global")
        code_local = DiscountCode.objects.get(identifier="local-first")
        self.assertIsNotNone(code_global.code)
        self.assertEqual(code_global.discount_percentage, 100)
        self.assertIsNone(code_global.plan)
        self.assertIsNone(code_global.usage_limit)
        self.assertEqual(code_local.code, DiscountCode.objects.prepare_code("slunicko"))
        self.assertIsNotNone(code_local.plan)
        self.assertEqual(code_local.usage_limit, 100)
        self.assertEqual(code_local.discount_percentage, 30)
