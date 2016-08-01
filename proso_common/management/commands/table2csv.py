# -*- coding: utf-8 -*-
from proso_common.models import get_tables_allowed_to_export
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import proso.django.db


class Command(BaseCommand):

    help = 'dump model to csv file in media directory'

    DEFAULT_BATCH_SIZE = 500000

    def handle(self, *args, **options):
        if len(args) > 0 and len(args) != 1:
            raise CommandError('''
            The command requires exactly one arguments:
                - table name
            or no argument.
            ''')
        batch_size = self.DEFAULT_BATCH_SIZE
        if hasattr(settings, 'PROSO_TABLE_EXPORT_BATCH_SIZE'):
            batch_size = settings.PROSO_TABLE_EXPORT_BATCH_SIZE
        if len(args) > 0:
            table_name = args[0]
            self.handle_one_table(table_name, batch_size)
        else:
            self.handle_all_tables(batch_size)

    def handle_all_tables(self, batch_size):
        for app, app_data in get_tables_allowed_to_export().items():
            for pk_column, table_name in app_data:
                self.handle_one_table(table_name, pk_column, batch_size)

    def handle_one_table(self, table_name, pk_column, batch_size):
        found = False
        for _, app_data in get_tables_allowed_to_export().items():
            if table_name in list(zip(*app_data))[1]:
                found = True
                break
        if not found:
            raise CommandError('table "%s" is not supported' % table_name)
        print('processing %s' % table_name)
        dest_file = settings.DATA_DIR + '/' + table_name + '.csv'
        proso.django.db.dump_table(table_name, pk_column, batch_size, dest_file)
