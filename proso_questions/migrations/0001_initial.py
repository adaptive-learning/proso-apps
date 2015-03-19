# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_models', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('url_name', models.SlugField(unique=True)),
                ('item', models.ForeignKey(null=True, default=None, blank=True, to='proso_models.Item', unique=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DecoratedAnswer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file', models.ImageField(max_length=255, upload_to=b'image/')),
                ('name', models.CharField(max_length=50)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Option',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.TextField()),
                ('order', models.IntegerField(default=None, null=True, blank=True)),
                ('correct', models.BooleanField(default=False)),
                ('item', models.ForeignKey(null=True, default=None, to='proso_models.Item', unique=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.SlugField(null=True, default=None, blank=True, unique=True)),
                ('text', models.TextField()),
                ('item', models.ForeignKey(null=True, default=None, blank=True, to='proso_models.Item', unique=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.SlugField(null=True, default=None, blank=True, unique=True)),
                ('text', models.TextField()),
                ('item', models.ForeignKey(null=True, default=None, blank=True, to='proso_models.Item', unique=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Set',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('item', models.ForeignKey(null=True, default=None, blank=True, to='proso_models.Item', unique=True)),
                ('questions', models.ManyToManyField(to='proso_questions.Question')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='question',
            name='resource',
            field=models.ForeignKey(related_name=b'resource_questions', default=None, blank=True, to='proso_questions.Resource', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='option',
            name='question',
            field=models.ForeignKey(related_name=b'question_options', to='proso_questions.Question'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='image',
            name='option',
            field=models.ForeignKey(related_name=b'option_images', default=None, blank=True, to='proso_questions.Option', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='image',
            name='question',
            field=models.ForeignKey(related_name=b'question_images', default=None, blank=True, to='proso_questions.Question', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='image',
            name='resource',
            field=models.ForeignKey(related_name=b'resource_images', default=None, blank=True, to='proso_questions.Resource', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='decoratedanswer',
            name='from_test',
            field=models.ForeignKey(default=None, blank=True, to='proso_questions.Set', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='decoratedanswer',
            name='general_answer',
            field=models.ForeignKey(to='proso_models.Answer', unique=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='category',
            name='questions',
            field=models.ManyToManyField(to='proso_questions.Question'),
            preserve_default=True,
        ),
    ]
