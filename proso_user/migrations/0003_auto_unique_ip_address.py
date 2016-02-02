# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_user', '0002_auto_unique_content_hash'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='ip_address',
            field=models.CharField(default=None, max_length=39, unique=True, null=True, blank=True),
            preserve_default=True,
        ),
    ]
