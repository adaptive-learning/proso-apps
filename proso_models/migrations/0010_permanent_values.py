# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.db import connection
from contextlib import closing


def remove_info_id(apps, schema_editor):
    with closing(connection.cursor()) as cursor:
        cursor.execute('UPDATE proso_models_variable SET info_id = NULL WHERE permanent')


class Migration(migrations.Migration):

    dependencies = [
        ('proso_models', '0009_remove_ab'),
    ]

    operations = [
        migrations.RunPython(remove_info_id)
    ]
