# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_common', '__first__'),
        ('proso_models', '0004_parent_child_permanency'),
    ]

    operations = [
        migrations.AddField(
            model_name='answer',
            name='config',
            field=models.ForeignKey(default=None, blank=True, to='proso_common.Config', null=True),
            preserve_default=True,
        ),
    ]
