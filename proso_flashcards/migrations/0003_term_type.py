# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_flashcards', '0002_auto_20150323_1300'),
    ]

    operations = [
        migrations.AddField(
            model_name='term',
            name='type',
            field=models.CharField(max_length=50, null=True, blank=True),
            preserve_default=True,
        ),
    ]
