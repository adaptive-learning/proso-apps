# -*- coding: utf-8 -*-
from proso_common.models import get_tables_allowed_to_export
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from contextlib import closing
import re
from django.conf import settings
import csv
import os
import os.path
import zipfile


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
        for table_name in get_tables_allowed_to_export():
            self.handle_one_table(table_name, batch_size)

    def handle_one_table(self, table_name, batch_size):
        if table_name not in get_tables_allowed_to_export():
            raise CommandError('table "%s" is not supported' % table_name)
        count = 0
        with closing(connection.cursor()) as cursor:
            cursor.execute('SELECT COUNT(*) FROM ' + table_name)
            count, = cursor.fetchone()
        print 'processing %s' % table_name, ',', count, 'items'
        sql = 'SELECT * FROM ' + table_name
        dest_file = settings.DATA_DIR + '/' + table_name
        dest_file_csv = dest_file + '.csv'
        dest_file_zip = dest_file + '.zip'
        for offset in xrange(0, count, batch_size):
            with closing(connection.cursor()) as cursor:
                cursor.execute(sql + ' LIMIT ' + str(batch_size) + ' OFFSET ' + str(offset))
                self.dump_cursor(
                    cursor,
                    dest_file_csv,
                    append=(offset > 0))
        if os.path.exists(dest_file_zip):
            os.remove(dest_file_zip)
        if os.path.exists(dest_file_csv):
            zf = zipfile.ZipFile(dest_file_zip, 'w', zipfile.ZIP_DEFLATED)
            zf.write(dest_file_csv, os.path.basename(dest_file_csv))
            zf.close()

    def dump_cursor(self, cursor, dest_file, append=False):
        headers = [re.sub(r'_id$', '', col[0]) for col in cursor.description]
        with open(dest_file, 'a' if append else 'w') as csvfile:
            writer = csv.writer(csvfile)
            if not append:
                writer.writerow(headers)
            for row in cursor:
                row = [val.encode('utf-8') if isinstance(val, unicode) else val for val in row]
                writer.writerow(row)
