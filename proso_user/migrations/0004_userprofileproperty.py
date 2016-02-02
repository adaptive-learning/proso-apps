# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_user', '0003_auto_unique_ip_address'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfileProperty',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=20, db_index=True)),
                ('value', models.CharField(max_length=200)),
                ('user_profile', models.ForeignKey(to='proso_user.UserProfile')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
