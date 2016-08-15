from django.apps import AppConfig as OAppConfig
from proso.django.enrichment import register_object_type_enricher


MIDDLEWARE_CLASSES = [
    'proso_models.middleware.InitPracticeFilterMiddleware',
]


class AppConfig(OAppConfig):

    name = 'proso_models'

    def ready(self):
        register_object_type_enricher(['item'], 'proso_models.json_enrich.item2object', priority=-1000000000, pure=False)
        register_object_type_enricher(['models_practice_set'], 'proso_models.json_enrich.answers_in_practice_set')
