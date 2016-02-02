# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('proso_user', '0004_userprofileproperty'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserQuestion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.SlugField()),
                ('lang', models.CharField(max_length=10)),
                ('content', models.TextField()),
                ('active', models.BooleanField(default=True)),
                ('answer_type', models.CharField(default='o', max_length=1, choices=[('c', 'closed'), ('m', 'mixed'), ('o', 'open')])),
                ('repeat', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserQuestionAnswer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('open_answer', models.CharField(default=None, max_length=100, null=True, blank=True)),
                ('time', models.DateTimeField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserQuestionCondition',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=50)),
                ('value', models.CharField(max_length=50)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserQuestionEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=50)),
                ('value', models.CharField(max_length=50)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserQuestionPossibleAnswer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.SlugField()),
                ('active', models.BooleanField(default=True)),
                ('content', models.CharField(max_length=100)),
                ('question', models.ForeignKey(related_name='possible_answers', to='proso_user.UserQuestion')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='userquestionanswer',
            name='closed_answer',
            field=models.ForeignKey(default=True, blank=True, to='proso_user.UserQuestionPossibleAnswer', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userquestionanswer',
            name='question',
            field=models.ForeignKey(related_name='user_answers', to='proso_user.UserQuestion'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userquestionanswer',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userquestion',
            name='conditions',
            field=models.ManyToManyField(to='proso_user.UserQuestionCondition'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userquestion',
            name='on_events',
            field=models.ManyToManyField(to='proso_user.UserQuestionEvent'),
            preserve_default=True,
        ),
    ]
