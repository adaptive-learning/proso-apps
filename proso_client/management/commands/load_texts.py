from django.core.management.base import BaseCommand, CommandError
from jsonschema import validate
import json
from django.db import transaction
from flatblocks.models import FlatBlock


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
                self._load_flatblocks(data)

    def _load_flatblocks(self, data):
        for d in data:
            try:
                flatblock = FlatBlock.objects.get(slug=d['slug'])
            except FlatBlock.DoesNotExist:
                flatblock = FlatBlock(
                    slug=d['slug'],
                )
            flatblock.header = d.get('header', None)
            flatblock.content = d.get('content', None)
            flatblock.save()
