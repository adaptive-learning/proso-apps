from django.apps import AppConfig as OAppConfig
from proso.django.enrichment import register_object_type_enricher


MIDDLEWARE_CLASSES = [
    'proso_subscription.middleware.CustomConfigFilterForActiveSubscription',
    'proso_subscription.middleware.ItemRestrictor',
]


class AppConfig(OAppConfig):

    name = 'proso_subscription'

    def ready(self):
        register_object_type_enricher(['subscription_plan_description'], 'proso_subscription.json_enrich.action_subscribe')
