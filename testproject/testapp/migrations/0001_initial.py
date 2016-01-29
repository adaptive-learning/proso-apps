# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_flashcards', '0002_auto_20150323_1300'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExtendedContext',
            fields=[
                ('context_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='proso_flashcards.Context')),
                ('extra_info', models.TextField()),
            ],
            options={
            },
            bases=('proso_flashcards.context',),
        ),
        migrations.CreateModel(
            name='ExtendedTerm',
            fields=[
                ('term_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='proso_flashcards.Term')),
                ('extra_info', models.TextField()),
            ],
            options={
            },
            bases=('proso_flashcards.term',),
        ),
    ]
