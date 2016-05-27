from django.apps import AppConfig as OAppConfig
from proso.django.enrichment import register_object_type_enricher
import proso_tasks.json_enrich as task_json_enrich


class AppConfig(OAppConfig):

    name = 'proso_tasks'

    def ready(self):
        register_object_type_enricher(['question'], task_json_enrich.answer_type)
