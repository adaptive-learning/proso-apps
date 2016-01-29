# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_user', '0001_initial'),
        ('proso_feedback', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('username', models.CharField(max_length=100, null=True, blank=True)),
                ('email', models.EmailField(max_length=75, null=True, blank=True)),
                ('text', models.TextField()),
                ('inserted', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(to='proso_user.Session')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
