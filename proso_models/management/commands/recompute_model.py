from django.core.management.base import BaseCommand
from django.conf import settings
import proso.util
from contextlib import closing
from django.db import connection
from proso_models.models import get_predictive_model


class Command(BaseCommand):

    def handle(self, *args, **options):
        if hasattr(settings, 'PROSO_RECOMPUTE_ENVIRONMENT') and settings.PROSO_RECOMPUTE_ENVIRONMENT is not None:
            env_class = settings.PROSO_RECOMPUTE_ENVIRONMENT
        else:
            env_class = 'proso_models.models.InMemoryDatabaseFlushEnvironment'
        environment = proso.util.instantiate(env_class)
        predictive_model = get_predictive_model()
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT
                    user_id,
                    item_primary_id,
                    item_secondary_id,
                    value,
                    updated,
                    key
                FROM proso_models_variable
                WHERE permanent
                ''')
            for row in cursor:
                environment.write(
                    row[5], row[3], user=row[0], item=row[1],
                    item_secondary=row[2], time=row[4], symmetric=False, permanent=True)
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT
                    user_id,
                    item_id,
                    item_asked_id,
                    item_answered_id,
                    time,
                    response_time,
                    guess
                FROM proso_models_answer
                ORDER BY id
                ''')
            for (user, item, asked, answered, time, response_time, guess) in cursor:
                predictive_model.predict_and_update(
                    environment,
                    user,
                    item,
                    asked == answered,
                    time,
                    item_answered=answered,
                    item_asked=asked)
                environment.process_answer(user, item, asked, answered, time, response_time, guess)
        environment.flush()
