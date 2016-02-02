# -*- coding: utf-8 -*-


from django.db import models, migrations
import datetime
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('inserted', models.DateTimeField(default=datetime.datetime.now)),
                ('value', models.SmallIntegerField(default=0, choices=[(0, 'Unknown'), (1, 'Too Easy'), (2, 'Just Right'), (3, 'Too Hard')])),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
