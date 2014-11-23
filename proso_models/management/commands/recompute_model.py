from django.core.management.base import BaseCommand
from django.conf import settings
import proso.util
from contextlib import closing
from django.db import connection
import re
import datetime
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
                    updated
                FROM proso_models_variable
                WHERE
                    key = 'parent'
                ''')
            for row in cursor:
                environment.write(
                    'parent', row[3], user=row[0], item=row[1],
                    item_secondary=row[2], time=self._ensure_is_datetime(row[4]), symmetric=False)
                environment.write(
                    'child', row[3], user=row[0], item=row[2],
                    item_secondary=row[1], time=self._ensure_is_datetime(row[4]), symmetric=False)
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
                time = self._ensure_is_datetime(time)
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

    def _ensure_is_datetime(self, value):
        if isinstance(value, datetime.datetime) or value is None:
            return value
        else:
            matched = re.match(r'([\d -\:]*)\.\d+', value)
            if matched is not None:
                value = matched.groups()[0]
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
