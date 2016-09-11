# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from proso.django.db import connection
from proso_common.models import get_events_logger, get_events_pusher


class Command(BaseCommand):
    help = 'Import answers to events storage. Example: python manage.py answers2events 2013-01-01 2014-01-01'

    def add_arguments(self, parser):
        parser.add_argument('from', type=str)
        parser.add_argument('to', type=str)

    def handle(self, *args, **options):
        logger = get_events_logger()
        pusher = get_events_pusher()

        with connection.cursor() as cursor:
            cursor.execute("select * from proso_models_answer where time >= %s::date and time < %s::date", (options['from'], options['to']))

            i = 1
            for row in cursor:
                answer = {
                    "user_id": row[6],
                    "is_correct": row[4] == row[5],
                    "context_id": [row[10]] if row[10] else [],
                    "item_id": row[3],
                    "response_time_ms": row[2],
                    "params": {
                        "session_id": row[8],
                        "guess": round(row[7], 5)
                    }}

                if row[9]: answer["params"]["config_id"] = row[9],

                logger.emit('answer', answer, time=row[1])

                if i % 5000 == 0:
                    self.stdout.write(str(i))
                    pusher.push_all()

                i += 1

            pusher.push_all()

            self.stdout.write(self.style.SUCCESS('Successfully sent events.'))
