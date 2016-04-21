from django.db import migrations


def drop_all_environment_relations(apps, schema_editor):
    Variable = apps.get_model('proso_models', 'Variable')
    Variable.objects.filter(key__in=['parent', 'child']).delete()


def move_category_structure(apps, schema_editor):
    Category = apps.get_model('proso_flashcards', "Category")
    ItemRelation = apps.get_model('proso_models', 'ItemRelation')
    categories = Category.objects.prefetch_related('subcategories', 'terms', 'contexts').all()
    for category in categories:
        parent_id = category.item_id
        visible = category.not_in_model
        for subobject in list(category.subcategories.all()) + list(category.terms.all()) + list(category.contexts.all()):
            ItemRelation.objects.get_or_create(
                parent_id=parent_id,
                child_id=subobject.item_id,
                visible=visible
            )


def move_term_structure(apps, schema_editor):
    Term = apps.get_model('proso_flashcards', "Term")
    ItemRelation = apps.get_model('proso_models', 'ItemRelation')
    terms = Term.objects.prefetch_related('flashcards').all()
    for term in terms:
        parent_id = term.item_id
        for flashcard in term.flashcards.all():
            ItemRelation.objects.get_or_create(
                parent_id=parent_id,
                child_id=flashcard.item_id,
                visible=True
            )


def move_context_structure(apps, schema_editor):
    Context = apps.get_model('proso_flashcards', "Context")
    ItemRelation = apps.get_model('proso_models', 'ItemRelation')
    contexts = Context.objects.prefetch_related('flashcards').all()
    for context in contexts:
        parent_id = context.item_id
        for flashcard in context.flashcards.all():
            ItemRelation.objects.get_or_create(
                parent_id=parent_id,
                child_id=flashcard.item_id,
                visible=True
            )


class Migration(migrations.Migration):

    dependencies = [
        ('proso_models', '0014_auto_item_children'),
        ('proso_flashcards', '0012_auto_django_python3_conversion'),
    ]

    operations = [
        migrations.RunPython(drop_all_environment_relations),
        migrations.RunPython(move_category_structure),
        migrations.RunPython(move_term_structure),
        migrations.RunPython(move_context_structure),
    ]
