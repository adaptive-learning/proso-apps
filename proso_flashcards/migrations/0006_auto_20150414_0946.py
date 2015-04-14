# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_flashcards', '0005_auto_20150330_0513'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='contexts',
            field=models.ManyToManyField(related_name=b'categories', to='proso_flashcards.Context'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='category',
            name='flashcards',
            field=models.ManyToManyField(related_name=b'categories', to='proso_flashcards.Flashcard'),
            preserve_default=True,
        ),
    ]
