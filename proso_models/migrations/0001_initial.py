# -*- coding: utf-8 -*-


from django.db import models, migrations
import datetime
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('proso_ab', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time', models.DateTimeField(default=datetime.datetime.now)),
                ('response_time', models.IntegerField()),
                ('ab_values_initialized', models.BooleanField(default=False)),
                ('ip_address', models.CharField(default=None, max_length=39, null=True, blank=True)),
                ('ab_values', models.ManyToManyField(to='proso_ab.Value')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Audit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(max_length=50)),
                ('value', models.FloatField()),
                ('time', models.DateTimeField(default=datetime.datetime.now)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Variable',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(max_length=50)),
                ('value', models.FloatField()),
                ('audit', models.BooleanField(default=True)),
                ('updated', models.DateTimeField(default=datetime.datetime.now)),
                ('item_primary', models.ForeignKey(related_name=b'item_primary_variables', default=None, blank=True, to='proso_models.Item', null=True)),
                ('item_secondary', models.ForeignKey(related_name=b'item_secondary_variables', default=None, blank=True, to='proso_models.Item', null=True)),
                ('user', models.ForeignKey(default=None, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='variable',
            unique_together=set([('key', 'user', 'item_primary', 'item_secondary')]),
        ),
        migrations.AlterIndexTogether(
            name='variable',
            index_together=set([('key', 'user', 'item_primary'), ('key', 'user'), ('key', 'user', 'item_primary', 'item_secondary'), ('key', 'item_primary')]),
        ),
        migrations.AddField(
            model_name='audit',
            name='item_primary',
            field=models.ForeignKey(related_name=b'item_primary_audits', default=None, blank=True, to='proso_models.Item', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='audit',
            name='item_secondary',
            field=models.ForeignKey(related_name=b'item_secondary_audits', default=None, blank=True, to='proso_models.Item', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='audit',
            name='user',
            field=models.ForeignKey(default=None, blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AlterIndexTogether(
            name='audit',
            index_together=set([('key', 'user', 'item_primary'), ('key', 'user'), ('key', 'user', 'item_primary', 'item_secondary'), ('key', 'item_primary')]),
        ),
        migrations.AddField(
            model_name='answer',
            name='item',
            field=models.ForeignKey(related_name=b'item_answers', to='proso_models.Item'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='answer',
            name='item_answered',
            field=models.ForeignKey(related_name=b'item_answered_answers', default=None, blank=True, to='proso_models.Item', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='answer',
            name='item_asked',
            field=models.ForeignKey(related_name=b'item_asked_answers', to='proso_models.Item'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='answer',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
