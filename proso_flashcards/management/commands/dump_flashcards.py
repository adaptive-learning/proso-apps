import json
from optparse import make_option

from django.conf import settings
import os
from django.core.management.base import BaseCommand
from jsonschema import validate

from proso_flashcards.models import Category, Context, Term, Flashcard


class Command(BaseCommand):
    help = "Dump flashcards to JSON file"

    option_list = BaseCommand.option_list + (
        make_option(
            '--flashcards',
            dest='flashcards',
            action='store_true',
            default=False,
            help='Include flashcards'),
        make_option(
            '--contexts',
            dest='contexts',
            action='store_true',
            default=False,
            help='Include contexts'),
        make_option(
            '--categories',
            dest='categories',
            action='store_true',
            default=False,
            help='Include categories'),
        make_option(
            '--terms',
            dest='terms',
            action='store_true',
            default=False,
            help='Include terms'),
        make_option(
            '--all',
            dest='all',
            action='store_true',
            default=False,
            help='Include all types of objects'),
    )

    def handle(self, *args, **options):
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "schema.json"), "r", encoding='utf8') as schema_file:
            schema = json.load(schema_file)

        data = {}
        if options["categories"] or options["all"]:
            data["categories"] = self._dump_categories()
        if options["contexts"] or options["all"]:
            data["contexts"] = self._dump_contexts()
        if options["terms"] or options["all"]:
            data["terms"] = self._dump_terms()
        if options["flashcards"] or options["all"]:
            data["flashcards"] = self._dump_flashcards()

        validate(data, schema)
        print((json.dumps(data, indent=4)))

    def _dump_categories(self, data=None):
        data = []
        for category in Category.objects.distinct("identifier").prefetch_related("parents").order_by("identifier"):
            c = {"id": category.identifier, "display-priority": category.display_priority}
            if category.type is not None:
                c["type"] = category.type
            for c2 in Category.objects.filter(identifier=category.identifier).order_by("lang"):
                c["name-{}".format(c2.lang)] = c2.name
            categories = category.parents.all().values_list("identifier", flat=True)
            if len(categories) > 0:
                c["categories"] = list(categories)
            data.append(c)
        return data

    def _dump_contexts(self):
        data = []
        for context in settings.PROSO_FLASHCARDS.get("context_extension", Context)\
                .objects.distinct("identifier").prefetch_related("categories").order_by("identifier"):
            c = {"id": context.identifier}
            if hasattr(context, "dump_data"):
                context.dump_data(c)
            for c2 in Context.objects.filter(identifier=context.identifier).order_by("lang"):
                c["name-{}".format(c2.lang)] = c2.name
                c["content-{}".format(c2.lang)] = c2.content
            categories = context.categories.all().values_list("identifier", flat=True)
            if len(categories) > 0:
                c["categories"] = list(categories)
            data.append(c)
        return data

    def _dump_terms(self, data=None):
        data = []
        for term in settings.PROSO_FLASHCARDS.get("term_extension", Term) \
                .objects.distinct("identifier").prefetch_related("parents").order_by("identifier"):
            t = {"id": term.identifier}
            if term.type is not None:
                t["type"] = term.type
            if hasattr(term, "dump_data"):
                term.dump_data(t)
            for t2 in Term.objects.filter(identifier=term.identifier).order_by("lang"):
                t["name-{}".format(t2.lang)] = t2.name
            categories = term.parents.all().values_list("identifier", flat=True)
            if len(categories) > 0:
                t["categories"] = list(categories)
            data.append(t)
        return data

    def _dump_flashcards(self):
        data = []
        for flashcard in Flashcard.objects.distinct("identifier").prefetch_related("categories")\
                .select_related("term", "context").order_by("identifier"):
            fc = {
                "id": flashcard.identifier,
                "term": flashcard.term.identifier,
                "context": flashcard.context.identifier,
                "active": flashcard.active,
            }
            if flashcard.description is not None:
                fc["description"] = flashcard.description
            if flashcard.additional_info is not None:
                fc['additional-info'] = flashcard.additional_info
            if flashcard.term_secondary is not None:
                fc['term-secondary'] = flashcard.term_secondary.identifier
            categories = flashcard.categories.all().values_list("identifier", flat=True)
            if len(categories) > 0:
                fc["categories"] = list(categories)
            data.append(fc)
        return data
