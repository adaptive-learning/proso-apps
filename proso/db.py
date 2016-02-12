from contextlib import closing
from django.db import connection
import csv
import re


def dump_table(table_name, pk_column, batch_size, dest_file):
    with closing(connection.cursor()) as cursor:
        cursor.execute('SELECT COUNT(*) FROM {}'.format(table_name))
        count, = cursor.fetchone()
    for offset in range(0, count, batch_size):
        with closing(connection.cursor()) as cursor:
            cursor.execute('SELECT * FROM {} ORDER BY {} LIMIT {} OFFSET {}'.format(table_name, pk_column, batch_size, offset))
            dump_cursor(
                cursor,
                dest_file,
                append=(offset > 0)
            )


def dump_cursor(cursor, dest_file, append=False):
    headers = [re.sub(r'_id$', '', col[0]) for col in cursor.description]
    with open(dest_file, 'a' if append else 'w') as csvfile:
        writer = csv.writer(csvfile)
        if not append:
            writer.writerow(headers)
        for row in cursor:
            row = [str(val) for val in row]
            writer.writerow(row)
