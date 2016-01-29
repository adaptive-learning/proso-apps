# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_models', '0010_permanent_values'),
    ]

    operations = [
        migrations.AddField(
            model_name='audit',
            name='answer',
            field=models.ForeignKey(default=None, blank=True, to='proso_models.Answer', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='variable',
            name='answer',
            field=models.ForeignKey(default=None, blank=True, to='proso_models.Answer', null=True),
            preserve_default=True,
        ),
    ]
