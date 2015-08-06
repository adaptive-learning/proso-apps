# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('proso_models', '0008_answer_meta'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AnswerExperimentSetup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('answer', models.ForeignKey(to='proso_models.Answer')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Experiment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.CharField(unique=True, max_length=100)),
                ('is_enabled', models.BooleanField(default=True)),
                ('is_paused', models.BooleanField(default=False)),
                ('time_disabled', models.DateTimeField(default=None, null=True, blank=True)),
                ('time_created', models.DateTimeField(default=datetime.datetime.now)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExperimentSetup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content_hash', models.CharField(unique=True, max_length=40)),
                ('experiment', models.ForeignKey(blank=True, to='proso_configab.Experiment', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PossibleValue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(max_length=100)),
                ('probability', models.IntegerField(default=0)),
                ('experiment', models.ForeignKey(to='proso_configab.Experiment')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserSetup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('experiment_setup', models.ForeignKey(to='proso_configab.ExperimentSetup')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, unique=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Variable',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('app_name', models.CharField(max_length=100)),
                ('name', models.CharField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='possiblevalue',
            name='variable',
            field=models.ForeignKey(to='proso_configab.Variable'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='possiblevalue',
            unique_together=set([('variable', 'experiment', 'value')]),
        ),
        migrations.AddField(
            model_name='experimentsetup',
            name='values',
            field=models.ManyToManyField(to='proso_configab.PossibleValue'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='answerexperimentsetup',
            name='experiment_setup',
            field=models.ForeignKey(to='proso_configab.ExperimentSetup'),
            preserve_default=True,
        ),
    ]
