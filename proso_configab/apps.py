from django.apps import AppConfig as OAppConfig
from proso.django.enrichment import register_object_type_enricher

MIDDLEWARE_CLASSES = [
    'proso_configab.models.ABConfigMiddleware',
]


class AppConfig(OAppConfig):

    name = 'proso_configab'

    def ready(self):
        register_object_type_enricher(['configab_experiment_setup'], 'proso_configab.json_enrich.experiment_setup_stats')
