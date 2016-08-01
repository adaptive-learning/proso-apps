# -*- coding: utf-8 -*-
from contextlib import closing
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db import transaction
from proso_common.models import get_custom_exports
from proso.django.db import is_on_postgresql
import proso.django.db
import uuid


class Command(BaseCommand):

    help = 'dump model to csv file in media directory'

    DEFAULT_BATCH_SIZE = 500000

    def handle(self, *args, **options):
        if len(args) > 0:
            raise CommandError('The command does not allow any argument.')
        batch_size = self.DEFAULT_BATCH_SIZE
        if hasattr(settings, 'PROSO_TABLE_EXPORT_BATCH_SIZE'):
            batch_size = settings.PROSO_TABLE_EXPORT_BATCH_SIZE
        self.handle_all(batch_size)

    def handle_all(self, batch_size):
        for app, app_data in get_custom_exports().items():
            for name, sql in app_data.items():
                self.handle_one_export(name, sql, batch_size)

    def handle_one_export(self, name, sql, batch_size):
        if is_on_postgresql():
            sql = '({})'.format(sql)
        table_name = 'tmp_{}'.format(str(uuid.uuid1()).replace('-', '_'))
        with transaction.atomic():
            with closing(connection.cursor()) as cursor:
                print('processing {}'.format(name))
                cursor.execute('CREATE TABLE {} AS {}'.format(table_name, sql))
                cursor.execute('SELECT COUNT(*) FROM {}'.format(table_name))
                count, = cursor.fetchone()
                dest_file = settings.DATA_DIR + '/' + name + '.csv'
                proso.django.db.dump_table(table_name, 'id', batch_size, dest_file)
                cursor.execute('DROP TABLE {}'.format(table_name))
