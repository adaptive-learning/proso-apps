from django.db import migrations


def migrate_category_types(apps, schema_editor):
    Category = apps.get_model('proso_flashcards', 'Category')
    ItemRelation = apps.get_model('proso_models', 'ItemRelation')
    for category in Category.objects.all():
        if not category.type:
            continue
        parent_category = Category.objects.get_or_create(
            identifier=category.type,
            name=category.type,
            lang=category.lang
        )
        ItemRelation.objects.get_or_create(
            parent_id=parent_category.item_id,
            child_id=category.item_id,
            visible=True
        )


def migrate_term_types(apps, schema_editor):
    Category = apps.get_model('proso_flashcards', 'Category')
    Term = apps.get_model('proso_flashcards', 'Term')
    ItemRelation = apps.get_model('proso_models', 'ItemRelation')
    for term in Term.objects.all():
        if not term.type:
            continue
        parent_category = Category.objects.get_or_create(
            identifier=term.type,
            name=term.type,
            lang=term.lang
        )
        ItemRelation.objects.get_or_create(
            parent_id=parent_category.item_id,
            child_id=term.item_id,
            visible=True
        )


class Migration(migrations.Migration):

    dependencies = [
        ('proso_flashcards', '0014_drop_redundant_structure_fields'),
    ]

    operations = [
        migrations.RunPython(migrate_category_types),
        migrations.RunPython(migrate_term_types),
    ]
