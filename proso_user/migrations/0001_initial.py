# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='HttpUserAgent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content', models.TextField()),
                ('content_hash', models.CharField(max_length=40, db_index=True)),
                ('device_family', models.CharField(default=None, max_length=50, null=True, blank=True)),
                ('os_family', models.CharField(default=None, max_length=39, null=True, blank=True)),
                ('os_version', models.CharField(default=None, max_length=39, null=True, blank=True)),
                ('browser_family', models.CharField(default=None, max_length=39, null=True, blank=True)),
                ('browser_version', models.CharField(default=None, max_length=39, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ip_address', models.CharField(default=None, max_length=39, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Session',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('locale', models.CharField(default=None, max_length=50, null=True, blank=True)),
                ('display_width', models.IntegerField(default=None, null=True, blank=True)),
                ('display_height', models.IntegerField(default=None, null=True, blank=True)),
                ('http_user_agent', models.ForeignKey(default=None, blank=True, to='proso_user.HttpUserAgent', null=True)),
                ('location', models.ForeignKey(default=None, blank=True, to='proso_user.Location', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TimeZone',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content', models.TextField()),
                ('content_hash', models.CharField(max_length=40, db_index=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('send_emails', models.BooleanField(default=True)),
                ('public', models.BooleanField(default=False)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='session',
            name='time_zone',
            field=models.ForeignKey(default=None, blank=True, to='proso_user.TimeZone', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='session',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
