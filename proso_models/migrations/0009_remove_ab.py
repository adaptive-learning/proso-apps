# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_models', '0008_answer_meta'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='answer',
            name='ab_values',
        ),
        migrations.RemoveField(
            model_name='answer',
            name='ab_values_initialized',
        ),
    ]
