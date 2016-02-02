# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_flashcards', '0010_auto_20150514_1137'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='flashcardanswer',
            name='meta',
        ),
    ]
