import json
from optparse import make_option

from clint.textui import progress
from django.conf import settings
from django.db.models import Count
import os
from django.core.management.base import BaseCommand, CommandError
from jsonschema import validate
from django.db import transaction
import re
import copy

from proso_flashcards.models import Category, Context, Term, Flashcard


class Command(BaseCommand):
    help = u"Load flashcards from JSON file"
    option_list = BaseCommand.option_list + (
        make_option(
            '--skip-category-check',
            dest='skip_category_check',
            default=False,
            action="store_true",
            help='Do not check if categories children are only of one type. Also correct type of categories is not set.'),
        make_option(
            '--skip-language-check',
            dest='skip_language_check',
            default=False,
            action="store_true",
            help='Do not check if for objects (Terms, Categoreies, etc.) for any given identifier exist for each language.'),
        make_option(
            '--ignored-flashcards',
            dest='ignored_flashcards',
            choices=['disable', 'delete'],
            default=None,
            help='Set strategy [delete|disable] in case of flashcards which are not mentioned for loaded context.',
        )
    )

    def handle(self, *args, **options):
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "schema.json"), "r") as schema_file:
            schema = json.load(schema_file, 'utf-8')
        if len(args) < 1:
            raise CommandError(
                "Not enough arguments. One argument required: " +
                " <file> JSON file containing questions")
        with open(args[0], 'r') as json_file:
            with transaction.atomic():
                data = json.load(json_file, 'utf-8')
                validate(data, schema)
                if "categories" in data:
                    self._load_categories(data["categories"])
                if "contexts" in data:
                    self._load_contexts(data["contexts"])
                if "terms" in data:
                    self._load_terms(data["terms"])
                if "flashcards" in data:
                    self._load_flashcards(data["flashcards"], options['ignored_flashcards'])
                if not options["skip_category_check"]:
                    check_and_set_category_type(Category)
                if not options["skip_language_check"]:
                    check_db_lang_integrity()

    def _load_categories(self, data=None):
        if data is not None:
            print "\nLoading categories"
        db_categories = {}
        item_mapping = {}
        for db_category in Category.objects.all().select_related("parents"):
            db_categories[db_category.identifier + db_category.lang] = db_category
            item_mapping[db_category.identifier] = db_category.item_id
        if data is None:
            return db_categories

        for category in progress.bar(data, every=max(1, len(data) / 100)):
            langs = [k[-2:] for k in category.keys() if re.match(r'^name-\w\w$', k)]
            for lang in langs:
                db_category = Category.objects.filter(identifier=category["id"], lang=lang).first()
                if db_category is None:
                    db_category = Category(
                        identifier=category["id"],
                        lang=lang,
                    )
                db_category.name = category["name-{}".format(lang)]
                if "not-in-model" in category:
                    db_category.not_in_model = category["not-in-model"]
                if "type" in category:
                    db_category.type = category["type"]
                if db_category.identifier in item_mapping:
                    db_category.item_id = item_mapping[db_category.identifier]
                    db_category.save()
                else:
                    db_category.save()
                    item_mapping[db_category.identifier] = db_category.item_id
                db_categories[db_category.identifier + db_category.lang] = db_category

        print "\nBuilding dependencies"
        for category in progress.bar(data, every=max(1, len(data) / 100)):
            for lang in [k[-2:] for k in category.keys() if re.match(r'^name-\w\w$', k)]:
                db_category = db_categories[category["id"] + lang]
                db_category.parents.clear()
                if "parent-categories" in category:
                    for parent in category["parent-categories"]:
                        if parent + lang not in db_categories:
                            raise CommandError(
                                "Parent category {} (lang {}) for category {} doesn't exist".format(parent, lang,
                                                                                          category["id"]))
                        db_category.parents.add(db_categories[parent + lang])
                db_category.save()

        print "New total number of categories in DB: {}".format(len(db_categories))
        return db_categories

    def _load_contexts(self, data=None):
        if data is not None:
            print "\nLoading contexts"
        model = settings.PROSO_FLASHCARDS.get("context_extension", Context)
        db_contexts = {}
        item_mapping = {}
        for db_context in model.objects.all():
            db_contexts[db_context.identifier + db_context.lang] = db_context
            item_mapping[db_context.identifier] = db_context.item_id
        if data is None:
            return db_contexts

        for context in progress.bar(data, every=max(1, len(data) / 100)):
            langs = [k[-2:] for k in context.keys() if re.match(r'^name-\w\w$', k)]
            for lang in langs:
                db_context = model.objects.filter(identifier=context["id"], lang=lang).first()
                if db_context is None:
                    db_context = model(
                        identifier=context["id"],
                        lang=lang,
                    )
                db_context.name = context["name-{}".format(lang)]
                content_key = "content-{}".format(lang)
                if content_key in context:
                    db_context.content = context[content_key]
                elif 'content' in context:
                    db_context.content = context['content']
                else:
                    raise CommandError(
                        'There is no content for context %s, language %s' % (db_context.identifier, lang))
                if "load_data" in model.__dict__:
                    model.load_data(context, db_context)
                if db_context.identifier in item_mapping:
                    db_context.item_id = item_mapping[db_context.identifier]
                    db_context.save()
                else:
                    db_context.save()
                    item_mapping[db_context.identifier] = db_context.item_id
                db_contexts[db_context.identifier + db_context.lang] = db_context

        categories = self._load_categories()
        print "\nBuilding dependencies"
        for context in progress.bar(data, every=max(1, len(data) / 100)):
            for lang in [k[-2:] for k in context.keys() if re.match(r'^name-\w\w$', k)]:
                db_context = db_contexts[context["id"] + lang]
                db_context.categories.clear()
                if "categories" in context:
                    for parent in context["categories"]:
                        if parent + lang not in categories:
                            raise CommandError(
                                "Parent category {} for context {} doesn't exist".format(parent + lang, context["id"]))
                        db_context.categories.add(categories[parent + lang])
                db_context.save()

        print "New total number of contexts in DB: {}".format(len(db_contexts))
        return db_contexts

    def _load_terms(self, data=None):
        if data is not None:
            print "\nLoading terms"
        model = settings.PROSO_FLASHCARDS.get("term_extension", Term)
        db_terms = {}
        item_mapping = {}
        for db_term in model.objects.all():
            db_terms[db_term.identifier + db_term.lang] = db_term
            item_mapping[db_term.identifier] = db_term.item_id
        if data is None:
            return db_terms

        for term in progress.bar(data, every=max(1, len(data) / 100)):
            langs = [k[-2:] for k in term.keys() if re.match(r'^name-\w\w$', k)]
            for lang in langs:
                db_term = model.objects.filter(identifier=term["id"], lang=lang).first()
                if db_term is None:
                    db_term = model(
                        identifier=term["id"],
                        lang=lang,
                    )
                db_term.name = term["name-{}".format(lang)]
                if "type" in term:
                    db_term.type = term["type"]
                if "load_data" in model.__dict__:
                    model.load_data(term, db_term)
                if db_term.identifier in item_mapping:
                    db_term.item_id = item_mapping[db_term.identifier]
                    db_term.save()
                else:
                    db_term.save()
                    item_mapping[db_term.identifier] = db_term.item_id
                db_terms[db_term.identifier + db_term.lang] = db_term

        categories = self._load_categories()
        print "\nBuilding dependencies"
        for term in progress.bar(data, every=max(1, len(data) / 100)):
            for lang in [k[-2:] for k in term.keys() if re.match(r'^name-\w\w$', k)]:
                db_term = db_terms[term["id"] + lang]
                db_term.parents.clear()
                if "categories" in term:
                    for parent in term["categories"]:
                        if parent + lang not in categories:
                            raise CommandError(
                                "Parent category {} for term {} doesn't exist".format(parent + lang, term["id"]))
                        db_term.parents.add(categories[parent + lang])
                db_term.save()

        print "New total number of terms in DB: {}".format(len(db_terms))
        return db_terms

    def _load_flashcards(self, data, ignored_flashcards_strategy):
        if data is not None:
            print "\nLoading flashcards"
        db_flashcards = {}
        db_flashcards_loaded = {}
        item_mapping = {}
        for db_flashcard in Flashcard.objects.all():
            db_flashcards[db_flashcard.identifier + db_flashcard.lang] = db_flashcard
            item_mapping[db_flashcard.identifier] = db_flashcard.item_id
        db_flascards_before_load = copy.copy(db_flashcards)

        for flashcard in progress.bar(data, every=max(1, len(data) / 100)):
            terms = Term.objects.filter(identifier=flashcard["term"])
            if len(terms) == 0:
                raise CommandError("Term {} for flashcard {} doesn't exist".format(flashcard["term"], flashcard["id"]))
            for term in terms:
                db_flashcard = Flashcard.objects.filter(identifier=flashcard["id"], lang=term.lang).first()
                context_id = Context.objects.filter(identifier=flashcard["context"], lang=term.lang).values_list("id", flat=True).first()
                if context_id is None:
                    raise CommandError(
                        "Context {} for flashcard {} doesn't exist".format(flashcard["context"], flashcard["id"]))
                if db_flashcard is None:
                    db_flashcard = Flashcard(
                        identifier=flashcard["id"],
                        lang=term.lang,
                    )
                db_flashcard.term = term
                db_flashcard.context_id = context_id
                if "description" in flashcard:
                    db_flashcard.description = flashcard["description"]
                if "active" in flashcard:
                    db_flashcard.active = flashcard["active"]
                if db_flashcard.identifier in item_mapping:
                    db_flashcard.item_id = item_mapping[db_flashcard.identifier]
                    db_flashcard.save()
                else:
                    db_flashcard.save()
                    item_mapping[db_flashcard.identifier] = db_flashcard.item_id
                db_flashcards_loaded[db_flashcard.identifier + db_flashcard.lang] = db_flashcard
                db_flashcards[db_flashcard.identifier + db_flashcard.lang] = db_flashcard

        print "\nChecking flashcards for loaded contexts"
        context_id_loaded = set(map(lambda db_flashcard: db_flashcard.context_id, db_flashcards_loaded.values()))
        db_flashcards_ignored = {
            key: db_flashcards[key]
            for key in (
                set({key: db_flashcard for (key, db_flashcard) in db_flascards_before_load.iteritems() if db_flashcard.context_id in context_id_loaded}.keys())
                -
                set(db_flashcards_loaded.keys())
            )
        }
        if len(db_flashcards_ignored) > 0:
            deleted_flashcard_items = set()
            print "\nThe following flashcards has been ignored during loading, action:", 'IGNORE' if ignored_flashcards_strategy is None else ignored_flashcards_strategy.upper()
            for db_flashcard in db_flashcards_ignored.itervalues():
                print ' --', db_flashcard.lang, ':', db_flashcard.identifier, ':', db_flashcard.context.identifier
                if ignored_flashcards_strategy == 'delete':
                    if db_flashcard.item_id not in deleted_flashcard_items:
                        deleted_flashcard_items.add(db_flashcard.item_id)
                        db_flashcard.item.delete()
                elif ignored_flashcards_strategy == 'disable':
                    db_flashcard.active = False
                    db_flashcard.save()

        categories = self._load_categories()
        print "\nBuilding dependencies"
        for flashcard in progress.bar(data, every=max(1, len(data) / 100)):
            for lang in Category.objects.all().values_list("lang", flat=True).distinct():
                db_flashcard = db_flashcards[flashcard["id"] + lang]
                db_flashcard.categories.clear()
                if "categories" in flashcard:
                    for parent in flashcard["categories"]:
                        if parent + lang not in categories:
                            raise CommandError(
                                "Parent category {} for flashcard {} doesn't exist".format(parent + lang, flashcard["id"]))
                        db_flashcard.categories.add(categories[parent + lang])
                db_flashcard.save()

        print "New total number of flashcards in DB: {}".format(len(db_flashcards))
        return db_flashcards


def check_db_lang_integrity():
    print "\nChecking DB language integrity"
    langs = Category.objects.all().values_list("lang", flat=True).distinct()
    print " -- languages: {}".format(langs)
    for model in [Category, Term, Flashcard, Context]:
        bad_objects = model.objects.all() \
            .values('identifier').annotate(Count("lang")).filter(lang__count__lt=len(langs))
        if len(bad_objects) > 0:
            raise CommandError(" -- {}s with wrong number of languages: {}".format(model.__name__, bad_objects))
    print " -- OK"


def check_and_set_category_type(dbCategory):
    for category in dbCategory.objects.all():
        terms = category.terms.all().count()
        flashcards = category.flashcards.all().count()
        contexts = category.contexts.all().count()
        subcategories = category.subcategories.all().count()
        all = terms + flashcards + contexts + subcategories
        if all == 0:
            print "Info: Category {} have no children".format(category.identifier)

        category.children_type = None
        if terms == all:
            category.children_type = Category.TERMS
        if flashcards == all:
            category.children_type = Category.FLASHCARDS
        if contexts == all:
            category.children_type = Category.CONTEXTS
        if subcategories == all:
            category.children_type = Category.CATEGORIES

        if category.children_type is None:
            raise AttributeError("Category {} have more types of children".format(category.identifier))

        category.save()
