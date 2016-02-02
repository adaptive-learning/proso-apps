# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_models', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.SlugField(default=None, null=True, blank=True)),
                ('name', models.CharField(max_length=100)),
                ('type', models.CharField(default=None, max_length=20, null=True, blank=True)),
                ('url_name', models.SlugField(unique=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DecoratedAnswer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('language', models.CharField(max_length=50)),
                ('direction', models.IntegerField(choices=[(1, 'reverse_asked'), (2, 'obverse_asked')])),
                ('category', models.ForeignKey(default=None, blank=True, to='proso_flashcards.Category', null=True)),
                ('general_answer', models.ForeignKey(related_name=b'flashcard_decoratedanswer_set', to='proso_models.Answer', unique=True)),
                ('options', models.ManyToManyField(related_name=b'flashcard_decoratedanswer_set', to='proso_models.Item')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Flashcard',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.SlugField(default=None, null=True, blank=True)),
                ('reverse', models.TextField()),
                ('obverse', models.TextField()),
                ('type', models.CharField(default=None, max_length=50, null=True, blank=True)),
                ('item', models.ForeignKey(default=None, blank=True, to='proso_models.Item', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='category',
            name='flashcards',
            field=models.ManyToManyField(to='proso_flashcards.Flashcard'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='category',
            name='item',
            field=models.ForeignKey(related_name=b'flashcard_category_set', default=None, blank=True, to='proso_models.Item', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='category',
            name='subcategories',
            field=models.ManyToManyField(related_name='subcategories_rel_+', to='proso_flashcards.Category'),
            preserve_default=True,
        ),
    ]
