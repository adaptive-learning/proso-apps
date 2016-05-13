from contextlib import closing
from django.conf import settings
from django.db import connection, migrations


def directions_to_types(apps, schema_editor):

    # Disable for tests
    if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
        return

    with closing(connection.cursor()) as cursor:
        cursor.execute(
            '''
            UPDATE proso_models_answer
            SET type = proso_flashcards_flashcardanswer.direction
            FROM proso_flashcards_flashcardanswer
            WHERE proso_models_answer.id = proso_flashcards_flashcardanswer.answer_ptr_id
            '''
        )


class Migration(migrations.Migration):

    dependencies = [
        ('proso_flashcards', '0016_drop_types'),
        ('proso_models', '0016_answer_type'),
    ]

    operations = [
        migrations.RunPython(directions_to_types),
    ]
