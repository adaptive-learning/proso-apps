# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_common', '0002_auto_20150416_0929'),
        ('proso_models', '0005_answer_config'),
    ]

    operations = [
        migrations.CreateModel(
            name='EnvironmentInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.IntegerField(default=1, choices=[(0, b'disabled'), (1, b'loading'), (2, b'enabled'), (3, b'active')])),
                ('revision', models.IntegerField()),
                ('load_progress', models.IntegerField(default=0)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('config', models.ForeignKey(to='proso_common.Config')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='environmentinfo',
            unique_together=set([('config', 'revision')]),
        ),
        migrations.AddField(
            model_name='audit',
            name='info',
            field=models.ForeignKey(default=None, blank=True, to='proso_models.EnvironmentInfo', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='variable',
            name='info',
            field=models.ForeignKey(default=None, blank=True, to='proso_models.EnvironmentInfo', null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='variable',
            unique_together=set([('info', 'key', 'user', 'item_primary', 'item_secondary')]),
        ),
        migrations.AlterIndexTogether(
            name='audit',
            index_together=set([('info', 'key'), ('info', 'key', 'user'), ('info', 'key', 'user', 'item_primary'), ('info', 'key', 'user', 'item_primary', 'item_secondary'), ('info', 'key', 'item_primary')]),
        ),
        migrations.AlterIndexTogether(
            name='variable',
            index_together=set([('info', 'key'), ('info', 'key', 'user'), ('info', 'key', 'user', 'item_primary'), ('info', 'key', 'user', 'item_primary', 'item_secondary'), ('info', 'key', 'item_primary')]),
        ),
    ]
