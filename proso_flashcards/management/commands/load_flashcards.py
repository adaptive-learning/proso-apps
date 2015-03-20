import json

import os
from django.core.management.base import BaseCommand, CommandError
from jsonschema import validate
from django.db import transaction
import re

from proso_flashcards.models import Category, Context, Term, Flashcard


class Command(BaseCommand):
    help = u"Load flashcards from JSON file"

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
                    _load_categories(data["categories"])
                if "contexts" in data:
                    _load_contexts(data["contexts"])
                if "terms" in data:
                    _load_terms(data["terms"])
                if "flashcards" in data:
                    _load_flashcards(data["flashcards"])


def _load_categories(data=None):
    db_categories = {}
    item_mapping = {}
    for db_category in Category.objects.all().select_related("parents"):
        db_categories[db_category.identifier] = db_category
        item_mapping[db_category.identifier] = db_category.item_id
    if data is None:
        return db_categories

    for category in data:
        langs = [k[-2:] for k in category.keys() if re.match(r'^name-\w\w$', k)]
        for lang in langs:
            db_category = Category.objects.filter(identifier=category["id"], lang=lang).first()
            if db_category is None:
                db_category = Category(
                    identifier=category["id"],
                    lang=lang,
                )
            db_category.name = category["name-{}".format(lang)]
            if "type" in category:
                db_category.type = category["type"]
            if db_category.identifier in item_mapping:
                db_category.item_id = item_mapping[db_category.identifier]
                db_category.save()
            else:
                db_category.save()
                item_mapping[db_category.identifier] = db_category.item_id
            db_categories[db_category.identifier] = db_category

    for category in data:
        db_category = db_categories[category["id"]]
        db_category.parents.clear()
        if "parent-categories" in category:
            for parent in category["parent-categories"]:
                if parent not in db_categories:
                    raise CommandError(
                        "Parent category {} for category {} doesn't exist".format(parent, category["id"]))
                db_category.parents.add(db_categories[parent])
        db_category.save()

    return db_categories


def _load_contexts(data=None):
    db_contexts = {}
    item_mapping = {}
    for db_context in Context.objects.all():
        db_contexts[db_context.identifier] = db_context
        item_mapping[db_context.identifier] = db_context.item_id
    if data is None:
        return db_contexts

    for context in data:
        langs = [k[-2:] for k in context.keys() if re.match(r'^name-\w\w$', k)]
        for lang in langs:
            db_context = Context.objects.filter(identifier=context["id"], lang=lang).first()
            if db_context is None:
                db_context = Context(
                    identifier=context["id"],
                    lang=lang,
                )
            db_context.name = context["name-{}".format(lang)]
            db_context.name = context["content-{}".format(lang)]
            if db_context.identifier in item_mapping:
                db_context.item_id = item_mapping[db_context.identifier]
                db_context.save()
            else:
                db_context.save()
                item_mapping[db_context.identifier] = db_context.item_id
            db_contexts[db_context.identifier] = db_context

            # TODO add support for context extensions

    return db_contexts


def _load_terms(data=None):
    db_terms = {}
    item_mapping = {}
    for db_term in Term.objects.all():
        db_terms[db_term.identifier] = db_term
        item_mapping[db_term.identifier] = db_term.item_id
    if data is None:
        return db_terms

    for term in data:
        langs = [k[-2:] for k in term.keys() if re.match(r'^name-\w\w$', k)]
        for lang in langs:
            db_term = Term.objects.filter(identifier=term["id"], lang=lang).first()
            if db_term is None:
                db_term = Term(
                    identifier=term["id"],
                    lang=lang,
                )
            db_term.name = term["name-{}".format(lang)]
            if db_term.identifier in item_mapping:
                db_term.item_id = item_mapping[db_term.identifier]
                db_term.save()
            else:
                db_term.save()
                item_mapping[db_term.identifier] = db_term.item_id
            db_terms[db_term.identifier] = db_term

            # TODO add support for terms extensions

    categories = _load_categories()
    for term in data:
        db_term = db_terms[term["id"]]
        db_term.parents.clear()
        if "categories" in term:
            for parent in term["categories"]:
                if parent not in categories:
                    raise CommandError(
                        "Parent category {} for term {} doesn't exist".format(parent, term["id"]))
                db_term.parents.add(categories[parent])
        db_term.save()

    return db_terms


def _load_flashcards(data):
    db_flashcards = {}
    item_mapping = {}
    for db_flashcard in Flashcard.objects.all():
        db_flashcards[db_flashcard.identifier] = db_flashcard
        item_mapping[db_flashcard.identifier] = db_flashcard.item_id
        
    for flashcard in data:
        terms = Term.objects.filter(identifier=flashcard["term"])
        if len(terms) == 0:
            raise CommandError("Term {} for flashcard {} doesn't exist".format(flashcard["term"], flashcard["id"]))
        for term in terms:
            db_flashcard = Flashcard.objects.filter(identifier=flashcard["id"], lang=term.lang).first()
            context = Context.objects.filter(identifier=flashcard["context"], lang=term.lang).first()
            if context is None:
                raise CommandError(
                    "Context {} for flashcard {} doesn't exist".format(flashcard["context"], flashcard["id"]))
            if db_flashcard is None:
                db_flashcard = Flashcard(
                    identifier=flashcard["id"],
                    lang=term.lang,
                    term=term,
                    context=context,
                )
            if "description" in flashcard:
                db_flashcard.description = flashcard["description"]
            if db_flashcard.identifier in item_mapping:
                db_flashcard.item_id = item_mapping[db_flashcard.identifier]
                db_flashcard.save()
            else:
                db_flashcard.save()
                item_mapping[db_flashcard.identifier] = db_flashcard.item_id
            db_flashcards[db_flashcard.identifier] = db_flashcard
            
    return db_flashcards