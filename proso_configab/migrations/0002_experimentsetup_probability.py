from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proso_configab', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='experimentsetup',
            name='probability',
            field=models.FloatField(blank=True, default=0, null=True),
        ),
    ]
