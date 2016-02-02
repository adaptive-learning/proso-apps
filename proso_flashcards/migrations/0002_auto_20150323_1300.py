# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_models', '0002_auto_20150323_1300'),
        ('proso_flashcards', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Context',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.SlugField()),
                ('lang', models.CharField(max_length=2)),
                ('name', models.TextField(null=True, blank=True)),
                ('content', models.TextField(null=True, blank=True)),
                ('item', models.ForeignKey(related_name=b'flashcard_contexts', default=None, to='proso_models.Item', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FlashcardAnswer',
            fields=[
                ('answer_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='proso_models.Answer')),
                ('direction', models.CharField(max_length=3, choices=[('t2d', 'From term to description'), ('d2t', 'From description to term')])),
                ('meta', models.TextField(null=True, blank=True)),
            ],
            options={
            },
            bases=('proso_models.answer',),
        ),
        migrations.CreateModel(
            name='Term',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('identifier', models.SlugField()),
                ('lang', models.CharField(max_length=2)),
                ('name', models.TextField()),
                ('item', models.ForeignKey(related_name=b'flashcard_terms', default=None, to='proso_models.Item', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='decoratedanswer',
            name='category',
        ),
        migrations.RemoveField(
            model_name='decoratedanswer',
            name='general_answer',
        ),
        migrations.RemoveField(
            model_name='decoratedanswer',
            name='options',
        ),
        migrations.DeleteModel(
            name='DecoratedAnswer',
        ),
        migrations.AddField(
            model_name='flashcardanswer',
            name='options',
            field=models.ManyToManyField(related_name=b'answers_with_this_as_option', to='proso_flashcards.Term'),
            preserve_default=True,
        ),
        migrations.RemoveField(
            model_name='category',
            name='flashcards',
        ),
        migrations.RemoveField(
            model_name='category',
            name='url_name',
        ),
        migrations.RemoveField(
            model_name='flashcard',
            name='obverse',
        ),
        migrations.RemoveField(
            model_name='flashcard',
            name='reverse',
        ),
        migrations.RemoveField(
            model_name='flashcard',
            name='type',
        ),
        migrations.AddField(
            model_name='category',
            name='lang',
            field=models.CharField(default='cs', max_length=2),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='category',
            name='terms',
            field=models.ManyToManyField(related_name=b'parents', to='proso_flashcards.Term'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='flashcard',
            name='context',
            field=models.ForeignKey(related_name=b'flashcards', default=None, to='proso_flashcards.Context'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='flashcard',
            name='description',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='flashcard',
            name='lang',
            field=models.CharField(default='cs', max_length=2),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='flashcard',
            name='term',
            field=models.ForeignKey(related_name=b'flashcards', default=None, to='proso_flashcards.Term'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='category',
            name='identifier',
            field=models.SlugField(),
        ),
        migrations.AlterField(
            model_name='category',
            name='item',
            field=models.ForeignKey(related_name=b'flashcard_categories', default=None, to='proso_models.Item', null=True),
        ),
        migrations.AlterField(
            model_name='category',
            name='name',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='category',
            name='subcategories',
            field=models.ManyToManyField(related_name=b'parents', to='proso_flashcards.Category'),
        ),
        migrations.AlterField(
            model_name='category',
            name='type',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='flashcard',
            name='identifier',
            field=models.SlugField(),
        ),
        migrations.AlterField(
            model_name='flashcard',
            name='item',
            field=models.ForeignKey(related_name=b'flashcards', default=None, to='proso_models.Item', null=True),
        ),
        migrations.AlterUniqueTogether(
            name='category',
            unique_together=None,
        ),
        migrations.AlterUniqueTogether(
            name='flashcard',
            unique_together=None,
        ),
    ]
