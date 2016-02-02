# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proso_flashcards', '0007_flashcard_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='children_type',
            field=models.CharField(max_length=1, null=True, choices=[(b'c', b'Category of categories'), (b't', b'Category of terms'), (b'f', b'Category of flashcards'), (b'x', b'Category of contexts')]),
            preserve_default=True,
        ),
    ]
