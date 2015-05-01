# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from proso_flashcards.management.commands.load_flashcards import check_and_set_category_type


def determine_category_type(apps, schema_editor):
    Category = apps.get_model("proso_flashcards", "Category")
    check_and_set_category_type(Category)


class Migration(migrations.Migration):

    dependencies = [
        ('proso_flashcards', '0008_category_children_type'),
    ]

    operations = [
        migrations.RunPython(determine_category_type),
    ]
