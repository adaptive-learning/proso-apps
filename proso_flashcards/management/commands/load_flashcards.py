from django.core.management.base import BaseCommand, CommandError
from jsonschema import validate
from proso_flashcards.models import Flashcard, Category, Context
from django.core.files import File
import json
from django.db import transaction
from clint.textui import progress
from collections import defaultdict
from django.utils.text import slugify
import os


class Command(BaseCommand):

    help = u"Load flashcards from JSON file"

    SCHEMA = {
        "description": "Schema for data containing flashcards",
        "definitions": {
            "category": {
                "type": "object",
                "properties": {
                    "context": {
                        "type": "string"
                    },
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
                    },
                    "subcategories": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["identifier", "name", "language"]
            },
            "context": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string"
                    },
                    "path": {
                        "type": "string"
                    },
                    "name": {
                        "type": "string"
                    },
                    "language": {
                        "type": "string"
                    }
                }
            },
            "flashcard": {
                "type": "object",
                "properties": {
                    "context": {
                        "type": "string"
                    },
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
            "contexts": {
                "type": "array",
                "items": {
                    "$ref": "#/definitions/context"
                }
            },
            "flashcards": {
                "type": "array",
                "items": {
                    "$ref": "#/definitions/flashcard"
                }
            }
        },
        "required": ["categories", "flashcards", "contexts"]
    }

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError(
                "Not enough arguments. One argument required: " +
                " <file> JSON file containing flashcards")
        working_directory = os.path.dirname(os.path.abspath(args[0]))
        with open(args[0], 'r') as json_data:
            with transaction.atomic():
                data = json.load(json_data, 'utf-8')
                validate(data, self.SCHEMA)
                self._reset_flashcards(data['flashcards'])
                context_provider = Provider(self._load_contexts(working_directory, data['contexts']), Context)
                category_provider = Provider(self._load_categories(data['categories'], context_provider), Category)
                self._load_flashcards(data['flashcards'], context_provider, category_provider)

    def _load_contexts(self, working_directory, contexts_data):
        print ' -- load contexts'
        contexts = defaultdict(dict)
        for context_data in progress.bar(contexts_data, every=(max(1, len(contexts_data) / 100))):
            language = context_data['language']
            lang_contexts = contexts[language]
            context_id = context_data['identifier']
            context = Context.objects.from_identifier(context_id, language)
            context.name = context_data['name']
            filename = os.path.join(working_directory, context_data['path'])
            with open(filename) as context_file:
                context.file.save(
                    slugify(context_id + '__' + language),
                    File(context_file))
            context.save()
            lang_contexts[context_id] = context
        return contexts

    def _load_categories(self, categories_data, context_provider):
        print ' -- load categories'
        categories = defaultdict(dict)
        for category_data in progress.bar(categories_data, every=max(1, len(categories_data) / 100)):
            language = category_data['language']
            lang_categories = categories[language]
            category_id = category_data['identifier']
            if category_id in lang_categories:
                raise CommandError(
                    "Category id has to be unique per language, '%s' defined twice" % category_id)
            category = Category.objects.from_identifier(category_id, language, reset=True)
            category.name = category_data['name']
            if 'context' in category_data:
                category.context = context_provider.provide(category_data['context'], language)
            else:
                category.context = None
            if 'type' in category_data:
                category.type = category_data['type']
            else:
                category.type = None
            for cats in categories.itervalues():
                if category_id in cats:
                    category.item = cats[category_id].item
                    break
            category.save()
            lang_categories[category_id] = category
        print ' -- load subcategories'
        for category_data in progress.bar(categories_data, every=max(1, len(categories_data) / 100)):
            language = category_data['language']
            lang_categories = categories[language]
            category_id = category_data['identifier']
            category = lang_categories[category_id]
            for subcategory_id in category_data.get('subcategories', []):
                subcategory = lang_categories.get(subcategory_id)
                if subcategory is None:
                    subcategory = Category.objects.get(identifier=subcategory_id, language=language)
                category.subcategories.add(subcategory)
            category.save()
        return categories

    def _reset_flashcards(self, flashcards_data):
        print ' -- reset flashcards'
        identifiers = defaultdict(list)
        for flashcard_data in progress.bar(flashcards_data, every=max(1, len(flashcards_data) / 100)):
            identifiers[flashcard_data['language']].append(flashcard_data['identifier'])
        for language, ids in identifiers.iteritems():
            Flashcard.objects.reset(
                Flashcard.objects.prefetch_related('category_set').filter(identifier__in=ids, language=language))

    def _load_flashcards(self, flashcards_data, context_provider, category_provider):
        print ' -- load flashcards'
        flashcards = defaultdict(dict)
        for flashcard_data in progress.bar(flashcards_data, every=max(1, len(flashcards_data) / 100)):
            language = flashcard_data['language']
            identifier = flashcard_data['identifier']
            flashcard = Flashcard.objects.from_identifier(identifier, language)
            flashcard.obverse = flashcard_data['obverse']
            flashcard.reverse = flashcard_data['reverse']
            if 'context' in flashcard_data:
                flashcard.context = context_provider.provide(flashcard_data['context'], language)
            else:
                flashcard.context = None
            if 'type' in flashcard_data:
                flashcard.type = flashcard_data['type']
            for flashs in flashcards.itervalues():
                if identifier in flashs:
                    flashcard.item = flashs[identifier].item
            flashcard.save()
            flashcards[language][identifier] = flashcard
            for category_id in flashcard_data['categories']:
                category_provider.provide(category_id, language).flashcards.add(flashcard)
        category_provider.save_all()


class Provider:

    def __init__(self, init_data, object_class):
        self._data = init_data
        self._object_class = object_class

    def provide(self, identifier, language):
        lang_data = self._data[language]
        result = lang_data.get(identifier)
        if result is None:
            result = self._object_class.objects.get(identifier=identifier, language=language)
            lang_data[identifier] = result
        return result

    def save_all(self):
        for data_lang in self._data.itervalues():
            for instance in data_lang.itervalues():
                instance.save()
