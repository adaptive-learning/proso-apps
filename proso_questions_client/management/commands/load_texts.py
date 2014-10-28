from django.core.management.base import BaseCommand, CommandError
from jsonschema import validate
import json
from django.db import transaction
from flatblocks.models import FlatBlock
import os


class Command(BaseCommand):
    help = u"""Load flatblock texts from json file to db."""

    SCHEMA = {
        "description": "Schema for data file containing texts",
        "definitions": {
            "flatblock": {
                "type": "object",
                "properties": {
                    "slug": {
                        "type": "string"
                    },
                    "header": {
                        "type": "string"
                    },
                    "content": {
                        "type": "string"
                    },
                    "contentfilename": {
                        "type": "string"
                    }
                },
                "required": ["slug"]
            },
        },
        "type": "array",
        "items": {
            "$ref": "#/definitions/flatblock"
        }
    }

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError(
                "Not enough arguments. One argument required: " +
                " <file> JSON file containing texts")
        with open(args[0], 'r') as json_data:
            with transaction.atomic():
                data = json.load(json_data, 'utf-8')
                validate(data, self.SCHEMA)
                folder_path = os.path.abspath(os.path.join(json_data.name, ".."))
                self._load_flatblocks(data, folder_path)

    def _load_flatblocks(self, data, folder_path):
        for d in data:
            try:
                flatblock = FlatBlock.objects.get(slug=d['slug'])
            except FlatBlock.DoesNotExist:
                flatblock = FlatBlock(
                    slug=d['slug'],
                )
            flatblock.header = d.get('header', None)
            flatblock.content = d.get('content', None)
            if 'contentfilename' in d:
                flatblock.content = file_get_contents(
                    os.path.join(folder_path, d['contentfilename']))
            flatblock.save()


def file_get_contents(filename):
    with open(filename) as f:
        return f.read()
