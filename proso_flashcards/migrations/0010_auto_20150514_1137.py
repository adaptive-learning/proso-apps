# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_flashcards', '0009_auto_20150430_1305'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='children_type',
            field=models.CharField(max_length=1, null=True, verbose_name=b'Category of', choices=[(b'c', b'categories'), (b't', b'terms'), (b'f', b'flashcards'), (b'x', b'contexts')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='flashcard',
            name='description',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
