# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_models', '0002_auto_20150323_1300'),
    ]

    operations = [
        migrations.AddField(
            model_name='variable',
            name='permanent',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
