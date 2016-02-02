# -*- coding: utf-8 -*-
# this migration is for purpose of migrating proso-apps to python3.5
from __future__ import unicode_literals

from django.db import models, migrations
import social.apps.django_app.default.fields
from django.conf import settings
import social.storage.django_orm
from social.utils import setting_name

user_model = getattr(settings, setting_name('USER_MODEL'), None) or \
    getattr(settings, 'AUTH_USER_MODEL', None) or 'auth.User'


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(user_model),
        ('proso_user', '0005_auto_user_questions'),
        ('default', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Code',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True,
                    primary_key=True)),
                ('email', models.EmailField(max_length=75)),
                ('code', models.CharField(max_length=32, db_index=True)),
                ('verified', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'social_auth_code',
            },
            bases=(models.Model, social.storage.django_orm.DjangoCodeMixin),
        ),
        migrations.AlterUniqueTogether(
            name='code',
            unique_together={('email', 'code')},
        ),
    ]
