from django.core.management.base import BaseCommand
from django.conf import settings
import proso.util
from contextlib import closing
from django.db import connection
import re
import datetime


class Command(BaseCommand):

    def handle(self, *args, **options):
        if hasattr(settings, 'PROSO_RECOMPUTE_ENVIRONMENT') and settings.PROSO_RECOMPUTE_ENVIRONMENT is not None:
            env_class = settings.PROSO_RECOMPUTE_ENVIRONMENT
        else:
            env_class = 'proso_models.models.InMemoryDatabaseFlushEnvironment'
        environment = proso.util.instantiate(env_class)
        predictive_model = proso.util.instantiate(settings.PROSO_PREDICTIVE_MODEL)
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT
                    user_id,
                    item_id,
                    item_asked_id,
                    item_answered_id,
                    time,
                    response_time
                FROM proso_models_answer
                ORDER BY id
                LIMIT 10000
                ''')
            for (user, item, asked, answered, time, response_time) in cursor:
                if not isinstance(time, datetime.datetime):
                    matched = re.match(r'([\d -\:]*)\.\d+', time)
                    if matched is not None:
                        time_string = matched.groups()[0]
                    else:
                        time_string = time
                    time = datetime.strptime(time_string, '%Y-%m-%d %H:%M:%S')
                predictive_model.predict_and_update(
                    environment,
                    user,
                    item,
                    asked == answered,
                    time,
                    item_answered=answered,
                    item_asked=asked)
                environment.process_answer(user, item, asked, answered, time, response_time)
        environment.flush()
