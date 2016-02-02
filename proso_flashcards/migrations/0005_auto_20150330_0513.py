# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_flashcards', '0004_auto_20150327_1241'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flashcardanswer',
            name='options',
            field=models.ManyToManyField(related_name=b'answers_with_this_as_option', to='proso_flashcards.Flashcard'),
        ),
    ]
