from django.core.management.base import BaseCommand, CommandError
from jsonschema import validate
from proso_questions.models import Resource, Image, Category, Set, Question, Option
from django.core.files import File
import os.path
import json
from django.db import transaction


class Command(BaseCommand):

    help = u"Load questions from JSON file"

    SCHEMA = {
        "description": "Schema for data file containing questions",
        "definitions": {
            "image": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string"
                    },
                    "name": {
                        "type": "string"
                    }
                },
                "required": ["path", "name"]
            },
            "option": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string"
                    },
                    "correct": {
                        "type": "boolean"
                    },
                    "order": {
                        "type": "number"
                    },
                    "images": {
                        "type": "array",
                        "items": {
                            "$ref": "#/definitions/image"
                        }
                    }
                },
                "required": ["text"]
            },
            "resource": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string"
                    },
                    "text": {
                        "type": "string"
                    },
                    "images": {
                        "type": "array",
                        "items": {
                            "$ref": "#/definitions/image"
                        }
                    }
                },
                "required": ["id", "text"]
            },
            "question": {
                "type": "object",
                "properties": {
                    "resource": {
                        "type": "string"
                    },
                    "category": {
                        "type": "string"
                    },
                    "sets": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "text": {
                        "type": "string"
                    },
                    "options": {
                        "type": "array",
                        "items": {
                            "$ref": "#/definitions/option"
                        }
                    }
                },
                "required": ["text", "options"]
            }
        },
        "type": "object",
        "properties": {
            "resources": {
                "type": "array",
                "items": {
                    "$ref": "#/definitions/resource"
                }
            },
            "questions": {
                "type": "array",
                "items": {
                    "$ref": "#/definitions/question"
                }
            }
        },
        "required": ["resources", "questions"]
    }

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError(
                "Not enough arguments. One argument required: " +
                " <file> JSON file containing questions")
        with open(args[0], 'r') as json_data:
            with transaction.atomic():
                data = json.load(json_data, 'utf-8')
                validate(data, self.SCHEMA)
                working_directory = os.path.dirname(os.path.abspath(args[0]))
                resources = self._load_resources(data, working_directory)
                self._load_questions(data, working_directory, resources)

    def _load_questions(self, data, working_directory, resources):
        categories = {}
        sets = {}
        for question_data in data['questions']:
            resource = question_data.get('resource', None)
            if resource is not None:
                resource = resources[resource]
            question = Question(
                text=question_data['text'],
                resource=resource)
            question.save()
            if 'sets' in question_data:
                for s in question_data['sets']:
                    if s not in sets:
                        sets[s] = Set.objects.from_name(s)
                    sets[s].questions.add(question)
            if 'categories' in question_data:
                for c in question_data['categories']:
                    if c not in categories:
                        categories[c] = Category.objects.from_name(c)
                    categories[c].questions.add(question)
            self._load_images(question_data, working_directory, question=question)
            one_option_correct = False
            for opt_data in question_data['options']:
                correct = bool(opt_data.get('correct', False))
                if correct:
                    if one_option_correct:
                        raise CommandError('At most one of the options has to be correct!')
                    one_option_correct = correct
                option = Option(
                    text=opt_data['text'],
                    question=question,
                    order=int(opt_data['order']) if 'order' in opt_data else None,
                    correct=correct
                    )
                option.save()
                self._load_images(opt_data, working_directory, option=option)
            if not one_option_correct:
                raise CommandError('At least one of the options has to be correct!')
        for s in sets.values():
            s.save()
        for c in categories.values():
            c.save()

    def _load_resources(self, data, working_directory):
        resources = {}
        for resource_data in data['resources']:
            resource_id = resource_data['id'].strip()
            if resource_id in resources:
                raise CommandError(
                    "Resource id has to be unique, '" + resource_id + "' defined twice.")
            resource = Resource(
                text=resource_data['text'])
            resource.save()
            resources[resource_id] = resource
            self._load_images(resource_data, working_directory, resource=resource)
        return resources

    def _load_images(self, data, working_directory, resource=None, question=None, option=None):
        if 'images' not in data:
            return
        for image_data in data['images']:
            image = Image(
                resource=resource,
                question=question,
                option=option,
                name=image_data['name'])
            filename = os.path.join(working_directory, image_data['path'])
            with open(filename) as image_file:
                image.file.save(
                    image_data['name'],
                    File(image_file))
                image.save()
