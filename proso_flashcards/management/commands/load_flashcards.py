from django.core.management.base import BaseCommand, CommandError
from jsonschema import validate
from proso_flashcards.models import Flashcard, Category
import json
from django.db import transaction
from clint.textui import progress
from collections import defaultdict


class Command(BaseCommand):

    help = u"Load flashcards from JSON file"

    SCHEMA = {
        "description": "Schema for data containing flashcards",
        "definitions": {
            "category": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string"
                    },
                    "type": {
                        "type": "string"
                    },
                    "name": {
                        "type": "string"
                    },
                    "language": {
                        "type": "string"
                    }
                },
                "required": ["identifier", "name", "language"]
            },
            "flashcard": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string"
                    },
                    "reverse": {
                        "type": "string"
                    },
                    "obverse": {
                        "type": "string"
                    },
                    "language": {
                        "type": "string"
                    },
                    "type": {
                        "type": "string"
                    },
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["identifier", "reverse", "obverse", "language"]
            }
        },
        "type": "object",
        "properties": {
            "categories": {
                "type": "array",
                "items": {
                    "$ref": "#/definitions/category"
                }
            },
            "flashcards": {
                "type": "array",
                "items": {
                    "$ref": "#/definitions/flashcard"
                }
            }
        },
        "required": ["categories", "flashcards"]
    }

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError(
                "Not enough arguments. One argument required: " +
                " <file> JSON file containing flashcards")
        with open(args[0], 'r') as json_data:
            with transaction.atomic():
                data = json.load(json_data, 'utf-8')
                validate(data, self.SCHEMA)
                self._reset_flashcards(data['flashcards'])
                categories = self._load_categories(data['categories'])
                self._load_flashcards(data['flashcards'], categories)

    def _load_categories(self, categories_data):
        print ' -- load categories'
        categories = defaultdict(dict)
        for category_data in progress.bar(categories_data, every=len(categories_data) / 100):
            language = category_data['language']
            lang_categories = categories[language]
            category_id = category_data['identifier']
            if category_id in lang_categories:
                raise CommandError(
                    "Category id has to be unique per language, '%s' defined twice" % category_id)
            category = Category.objects.from_identifier(category_id, language)
            category.name = category_data['name']
            if 'type' in category_data:
                category.type = category_data['type']
            for cats in categories.itervalues():
                if category_id in cats:
                    category.item = cats[category_id].item
                    break
            category.save()
            lang_categories[category_id] = category
        return categories

    def _reset_flashcards(self, flashcards_data):
        print ' -- reset flashcards'
        identifiers = defaultdict(list)
        for flashcard_data in progress.bar(flashcards_data, every=len(flashcards_data) / 100):
            identifiers[flashcard_data['language']].append(flashcard_data['identifier'])
        for language, ids in identifiers.iteritems():
            Flashcard.objects.reset(
                Flashcard.objects.prefetch_related('category_set').filter(identifier__in=ids, language=language))

    def _load_flashcards(self, flashcards_data, categories):
        print ' -- load flashcards'
        flashcards = defaultdict(dict)
        for flashcard_data in progress.bar(flashcards_data, every=len(flashcards_data) / 100):
            language = flashcard_data['language']
            identifier = flashcard_data['identifier']
            flashcard = Flashcard.objects.from_identifier(identifier, language)
            flashcard.obverse = flashcard_data['obverse']
            flashcard.reverse = flashcard_data['reverse']
            if 'type' in flashcard_data:
                flashcard.type = flashcard_data['type']
            for flashs in flashcards.itervalues():
                if identifier in flashs:
                    flashcard.item = flashs[identifier].item
            flashcard.save()
            flashcards[language][identifier] = flashcard
            for category_id in flashcard_data['categories']:
                categories[language][category_id].flashcards.add(flashcard)
        for lang_categories in categories.values():
            for category in lang_categories.values():
                category.save()
