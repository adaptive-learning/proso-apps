from django.apps import AppConfig as OAppConfig
from proso.django.enrichment import register_object_type_enricher


class AppConfig(OAppConfig):

    name = 'proso_user'

    def ready(self):
        register_object_type_enricher(['user_question'], 'proso_user.json_enrich.user_answers')
