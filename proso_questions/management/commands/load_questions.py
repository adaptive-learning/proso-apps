from django.core.management.base import BaseCommand, CommandError
from jsonschema import validate
from proso_questions.models import Resource, Image, Category, Set, Question, Option
from django.core.files import File
import os.path
import json
from django.db import transaction
from clint.textui import progress


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
                    "identifier": {
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
                "required": ["identifier", "text"]
            },
            "question": {
                "type": "object",
                "properties": {
                    "resource": {
                        "type": "string"
                    },
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "sets": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "identifier": {
                        "type": "string"
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
        print ' -- reset questions with identifier'
        identifiers_to_reset = []
        for question_data in data['questions']:
            if 'identifier' in question_data:
                identifiers_to_reset.append(question_data['identifier'])
        questions_with_identifiers = Question.objects.from_identifiers(identifiers_to_reset, reset=True)
        print ' -- load questions'
        for question_data in progress.bar(data['questions'], every=len(data['questions']) / 100):
            resource = question_data.get('resource', None)
            if resource is not None:
                resource = resources[resource]
            if 'identifier' in question_data:
                question = questions_with_identifiers[question_data['identifier']]
                question.identifier = question_data['identifier']
            else:
                question = Question()
            question.text = question_data['text']
            question.resource = resource
            question.save()
            if 'sets' in question_data:
                for s in question_data['sets']:
                    s = self._ensure_string(s)
                    if s not in sets:
                        sets[s] = Set.objects.from_name(s)
                    sets[s].questions.add(question)
            if 'categories' in question_data:
                for c in question_data['categories']:
                    c = self._ensure_string(c)
                    if c not in categories:
                        categories[c] = Category.objects.from_name(c)
                    categories[c].questions.add(question)
            self._load_images(question_data, working_directory, question=question)
            self._load_options(working_directory, question_data['options'], question)
        for s in sets.values():
            s.save()
        for c in categories.values():
            c.save()

    def _load_resources(self, data, working_directory):
        print ' -- load resources'
        resources = {}
        for resource_data in progress.bar(data['resources'], every=len(data['resources']) / 100):
            resource_id = resource_data['identifier'].strip()
            if resource_id in resources:
                raise CommandError(
                    "Resource id has to be unique, '" + resource_id + "' defined twice.")
            resource = Resource.objects.from_identifier(resource_id, reset=True)
            resource.text = resource_data['text']
            resource.save()
            resources[resource_id] = resource
            self._load_images(resource_data, working_directory, resource=resource)
        return resources

    def _load_options(self, working_directory, options_data, question):
        if question.identifier:
            options = Option.objects.from_question(question, reset=True)
            if len(options) > 0 and len(options) != len(options_data):
                raise CommandError(
                    "Can't change the number of options for the question %s" % question.identifier)
            if len(options) == 0:
                options = [Option() for i in options_data]
        else:
            options = [Option() for i in options_data]
        options = sorted(options, key=lambda o: o.order)
        options_data = sorted(options_data, key=lambda o: o.get('order', None))
        one_option_correct = False
        for opt, opt_data in zip(options, options_data):
            correct = bool(opt_data.get('correct', False))
            if correct:
                if one_option_correct:
                    raise CommandError('At most one of the options has to be correct!')
                one_option_correct = correct
            opt.text=opt_data['text']
            opt.question=question
            opt.order=int(opt_data['order']) if 'order' in opt_data else None
            opt.correct=correct
            opt.save()
            self._load_images(opt_data, working_directory, option=opt)
        if not one_option_correct:
            raise CommandError('At least one of the options has to be correct for question %s!' % question.identifier)

    def _load_images(self, data, working_directory, resource=None, question=None, option=None):
        if 'images' not in data:
            return
        for image_data in data['images']:
            if image_data['name'].rfind(' ') != -1:
                raise CommandError('The space in image name found: %s' % image_data['name'])
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

    def _ensure_string(self, value):
        if isinstance(value, int):
            value = unicode(str(value), "utf-8")
        return value
