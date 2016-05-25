from django.apps import AppConfig as OAppConfig
from proso.django.enrichment import register_object_type_enricher


class AppConfig(OAppConfig):

    name = 'proso_models'

    def ready(self):
        register_object_type_enricher(['item'], 'proso_models.json_enrich.item2object', priority=-1000000000, pure=False)
