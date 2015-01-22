from django.core.management.base import BaseCommand
import json
from django.db import connection
from django.core.management import call_command
from contextlib import closing
from django.db import transaction
from proso_flashcards.models import DecoratedAnswer
from collections import defaultdict


class Command(BaseCommand):

    def handle(self, *args, **options):
        with transaction.atomic():
            with closing(connection.cursor()) as cursor:
                cursor.execute('SET CONSTRAINTS ALL DEFERRED;')
            self.migrate_experiments()

    def migrate_experiments(self):
        print ' -- delete experiments'
        with closing(connection.cursor()) as cursor:
            cursor.execute('DELETE FROM proso_ab_uservalue CASCADE')
            cursor.execute('DELETE FROM proso_ab_value CASCADE')
            cursor.execute('DELETE FROM proso_ab_experiment CASCADE')
        print ' -- loading experiments'
        with closing(connection.cursor()) as cursor_source:
            cursor_source.execute('SELECT id, active, name FROM geography_ab_group')
            with closing(connection.cursor()) as cursor_dest:
                for row in cursor_source:
                    cursor_dest.execute(
                        '''
                        INSERT INTO proso_ab_experiment
                            (id, active, name)
                        VALUES (%s, %s, %s)
                        ''', row)
        print ' -- loading values'
        with closing(connection.cursor()) as cursor_source:
            cursor_source.execute(
                '''
                SELECT id, group_id, value, probability, is_default
                FROM geography_ab_value
                ''')
            with closing(connection.cursor()) as cursor_dest:
                for row in cursor_source:
                    cursor_dest.execute(
                        '''
                        INSERT INTO proso_ab_value
                            (id, experiment_id, name, probability, is_default)
                        VALUES (%s, %s, %s, %s, %s)
                        ''', row)
        print ' -- loading values for users'
        with closing(connection.cursor()) as cursor:
            cursor.execute('SELECT id, user_id FROM geography_ab_uservalues')
            uservalues = dict(cursor.fetchall())
        with closing(connection.cursor()) as cursor_source:
            cursor_source.execute(
                '''
                SELECT uservalues_id, value_id
                FROM geography_ab_uservalues_values
                ''')
            with closing(connection.cursor()) as cursor_dest:
                for row in cursor_source:
                    cursor_dest.execute(
                        '''
                        INSERT INTO proso_ab_uservalue
                            (user_id, value_id)
                        VALUES (%s, %s)
                        ''', [uservalues[row[0]], row[1]])




