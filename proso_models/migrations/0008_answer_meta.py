# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_models', '0007_practice_context'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnswerMeta',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content', models.TextField()),
                ('content_hash', models.CharField(unique=True, max_length=40, db_index=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='answer',
            name='metainfo',
            field=models.ForeignKey(default=None, blank=True, to='proso_models.AnswerMeta', null=True),
            preserve_default=True,
        ),
    ]
