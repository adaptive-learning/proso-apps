# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from proso.django.db import connection
from proso_common.models import get_events_logger, get_events_pusher
from clint.textui import progress


class Command(BaseCommand):
    help = 'Import answers to events storage. Example: python manage.py answers2events 2013-01-01 2014-01-01'

    def add_arguments(self, parser):
        parser.add_argument('from', type=str)
        parser.add_argument('to', type=str)

    def handle(self, *args, **options):
        events_log = 'answers2events.log'
        logger = get_events_logger(events_log)
        pusher = get_events_pusher(events_log)

        with connection.cursor() as cursor:
            cursor.execute("""
                select
                  user_id,
                  item_answered_id,
                  item_asked_id,
                  context_id,
                  item_id,
                  response_time,
                  session_id,
                  guess,
                  config_id,
                  time
                from proso_models_answer
                where time >= %s::date and time < %s::date
                order by time""", (options['from'], options['to']))

            i = 1
            for user_id, item_answered_id, item_asked_id, context_id, item_id, response_time, session_id, guess, config_id, time in progress.bar(cursor, expected_size=cursor.rowcount):
                answer = {
                    "user_id": user_id,
                    "is_correct": item_asked_id == item_answered_id,
                    "context_id": [context_id] if context_id else [],
                    "item_id": item_id,
                    "response_time_ms": response_time,
                    "params": {
                        "session_id": session_id,
                        "guess": guess
                    }}

                if config_id:
                    answer["params"]["config_id"] = config_id

                logger.emit('answer', answer, time=time)

                if i % 5000 == 0:
                    pusher.push_all()

                i += 1

            pusher.push_all()

            self.stdout.write(self.style.SUCCESS('Successfully sent events.'))
