from django.db import models, migrations
from django.db import connection
from contextlib import closing


def set_permanent(apps, schema_editor):
    with closing(connection.cursor()) as cursor:
        cursor.execute(
            '''
            UPDATE proso_models_variable
            SET permanent = (1 = 1)
            WHERE key = 'parent' OR key = 'child'
            ''')


class Migration(migrations.Migration):


    dependencies = [
        ('proso_models', '0003_variable_permanent'),
    ]

    operations = [
        migrations.RunPython(set_permanent),
    ]


