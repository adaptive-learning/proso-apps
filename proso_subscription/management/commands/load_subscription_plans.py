from clint.textui import progress
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from jsonschema import validate
from proso_subscription.models import SubscriptionPlan, SubscriptionPlanDescription, DiscountCode
import json
import os
import re


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('filename')

    def handle(self, *args, **options):
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "subscription_plans_schema.json"), "r", encoding='utf8') as schema_file:
            schema = json.load(schema_file)
        with open(options['filename'], 'r', encoding='utf8') as json_file:
            with transaction.atomic():
                data = json.load(json_file)
                validate(data, schema)
                self._load_plans(data['plans'])
                self._load_discount_codes(data.get('discount-codes', []))

    def _load_plans(self, data):
        print('Loading subscription plans')
        for plan_json in progress.bar(data):
            plan = SubscriptionPlan.objects.filter(identifier=plan_json['id']).first()
            if plan is None:
                plan = SubscriptionPlan(identifier=plan_json['id'])
            plan.months_validity = plan_json['months-validity']
            plan.months_referral = plan_json.get('months-referral', 0)
            plan.type = plan_json['type']
            plan.active = not plan_json.get('disabled', False)
            plan.featured = plan_json.get('featured', False)
            plan.save()
            langs = [k[-2:] for k in plan_json.keys() if re.match(r'^description-\w\w$', k)]
            for lang in langs:
                description_json = plan_json['description-{}'.format(lang)]
                description = SubscriptionPlanDescription.objects.filter(plan__identifier=plan.identifier, lang=lang).first()
                if description is None:
                    description = SubscriptionPlanDescription(plan=plan, lang=lang)
                description.currency = description_json['currency']
                description.price = description_json['price'] * 100
                description.name = description_json['name']
                description.description = description_json['description']
                description.save()

    def _load_discount_codes(self, data):
        print('Loading discount codes')
        for discount_code_json in progress.bar(data):
            discount_code = DiscountCode.objects.filter(identifier=discount_code_json['id']).first()
            if discount_code is None:
                discount_code = DiscountCode(
                    identifier=discount_code_json['id']
                )
            discount_code.discount_percentage = discount_code_json['discount-percentage']
            if discount_code.discount_percentage < 1 or discount_code.discount_percentage > 100:
                raise CommandError("The discount-percentage for discount code {} is out bounds [1, 100].".format(discount_code_json['id']))
            discount_code.active = not discount_code_json.get('disabled', False)
            if 'code' in discount_code_json:
                discount_code.code = DiscountCode.objects.prepare_code(discount_code_json['code'])
            if not discount_code.code:
                discount_code.code = DiscountCode.objects.generate_code()
            if 'usage-limit' in discount_code_json:
                discount_code.usage_limit = int(discount_code_json['usage-limit'])
            else:
                discount_code.usage_limit = None
            if 'plan' in discount_code_json:
                discount_code.plan = SubscriptionPlan.objects.get(identifier=discount_code_json['plan'])
            else:
                discount_code.plan = None
            discount_code.save()
