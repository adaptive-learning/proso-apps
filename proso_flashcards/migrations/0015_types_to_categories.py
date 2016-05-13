from django.core.management import call_command
from django.db import migrations


def migrate_term_types(apps, schema_editor):
    Category = apps.get_model('proso_flashcards', 'Category')
    Term = apps.get_model('proso_flashcards', 'Term')
    Item = apps.get_model('proso_models', 'Item')
    ItemRelation = apps.get_model('proso_models', 'ItemRelation')
    new_items = {}
    for term in Term.objects.all():
        if not term.type:
            continue
        parent_category, _ = Category.objects.get_or_create(
            identifier=term.type,
            name=term.type,
            lang=term.lang,
            type="flashcard_type"
        )
        if parent_category.item is None:
            if parent_category.identifier not in new_items:
                item = Item. objects.create()
                new_items[parent_category.identifier] = item
            parent_category.item = new_items[parent_category.identifier]
            parent_category.save()
        ItemRelation.objects.get_or_create(
            parent_id=parent_category.item.pk,
            child_id=term.item.pk,
            visible=True
        )
    call_command('fill_item_types')


class Migration(migrations.Migration):

    dependencies = [
        ('proso_flashcards', '0014_drop_redundant_structure_fields' ),
        ('proso_models', '0015_auto_item_activity' ),
    ]

    operations = [
        migrations.RunPython(migrate_term_types),
    ]
