from clint.textui import progress
from django.core.management.base import BaseCommand
from django.db import transaction
from jsonschema import validate
from proso_subscription.models import SubscriptionPlan, SubscriptionPlanDescription
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

    def _load_plans(self, data):
        for plan_json in progress.bar(data):
            plan = SubscriptionPlan.objects.filter(identifier=plan_json['id']).first()
            if plan is None:
                plan = SubscriptionPlan(identifier=plan_json['id'])
            plan.months_validity = plan_json['months-validity']
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
