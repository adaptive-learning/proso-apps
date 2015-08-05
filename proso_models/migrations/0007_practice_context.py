# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_models', '0006_environment_info'),
    ]

    operations = [
        migrations.CreateModel(
            name='PracticeContext',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content', models.TextField()),
                ('content_hash', models.CharField(unique=True, max_length=40, db_index=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='answer',
            name='context',
            field=models.ForeignKey(default=None, blank=True, to='proso_models.PracticeContext', null=True),
            preserve_default=True,
        ),
        migrations.AlterIndexTogether(
            name='answer',
            index_together=set([('user', 'context')]),
        ),
    ]
