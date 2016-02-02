# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_user', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='httpuseragent',
            name='content_hash',
            field=models.CharField(unique=True, max_length=40, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='timezone',
            name='content_hash',
            field=models.CharField(unique=True, max_length=40, db_index=True),
            preserve_default=True,
        ),
    ]
