# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_flashcards', '0006_auto_20150414_0946'),
    ]

    operations = [
        migrations.AddField(
            model_name='flashcard',
            name='active',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]
