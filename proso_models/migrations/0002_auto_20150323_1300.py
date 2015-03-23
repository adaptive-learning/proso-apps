# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_user', '0001_initial'),
        ('proso_models', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='answer',
            name='ip_address',
        ),
        migrations.AddField(
            model_name='answer',
            name='guess',
            field=models.FloatField(default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='answer',
            name='session',
            field=models.ForeignKey(default=None, blank=True, to='proso_user.Session', null=True),
            preserve_default=True,
        ),
    ]
