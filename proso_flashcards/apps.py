from django.apps import AppConfig as OAppConfig
from proso.django.enrichment import register_object_type_enricher


class AppConfig(OAppConfig):

    name = 'proso_flashcards'

    def ready(self):
        register_object_type_enricher(['fc_answer'], 'proso_flashcards.json_enrich.answer_flashcards')
        register_object_type_enricher(['fc_flashcard'], 'proso_models.json_enrich.prediction')
        register_object_type_enricher(['fc_flashcard', 'fc_category', 'fc_term', 'fc_context'], 'proso_models.json_enrich.number_of_answers')
        register_object_type_enricher(['fc_category', 'fc_term', 'fc_context'], 'proso_models.json_enrich.avg_prediction')
        register_object_type_enricher(['fc_context'], 'proso_flashcards.json_enrich.context_flashcards')
        register_object_type_enricher(['question'], 'proso_flashcards.json_enrich.answer_type')
        register_object_type_enricher(['question'], 'proso_flashcards.json_enrich.question_type', priority=-1000)
        register_object_type_enricher(['question'], 'proso_flashcards.json_enrich.options', dependencies=['proso_flashcards.json_enrich.question_type'], priority=-1000)
