from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction
from jsonschema import validate
import json
import os

from proso_concepts.models import Tag, Concept, Action


class Command(BaseCommand):
    help = "Load concepts from JSON file"

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=None, stderr=None, no_color=False)
        self.tags = {}
        self.concepts = {}

    def add_arguments(self, parser):
        parser.add_argument('filename', nargs=1, type=str)

    def handle(self, *args, **options):
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "schema.json"), "r") as schema_file:
            schema = json.load(schema_file)
        with open(options["filename"][0], 'r') as json_file:
            with transaction.atomic():
                data = json.load(json_file)
                validate(data, schema)

                self.prepare_tags(data)
                self.prepare_concepts()
                self.process_concepts(data["concepts"], data["action_names"], data["tags"])

                cache.clear()

        self.stdout.write("Successfully imported concepts")
        self.stdout.write("Total {} concepts and {} tags in DB".format(Concept.objects.all().count(),
                                                                    Tag.objects.all().count()))

    def prepare_tags(self, data):
        self.tag_names = data["tags"]

        for tag in Tag.objects.all():
            self.tags["{}:{}:{}".format(tag.type, tag.value, tag.lang)] = tag
            new_type_name = self.tag_names[tag.type]["names"][tag.lang]
            new_value_name=self.tag_names[tag.type]["values"][tag.value][tag.lang]
            if tag.type_name != new_type_name or tag.value_name != new_value_name:
                tag.type_name = new_type_name
                tag.value_name = new_value_name
                tag.save()

    def add_tag(self, tag, lang):
        parts = tag.split(":")
        self.tags["{}:{}".format(tag, lang)] = Tag.objects.create(
            type=parts[0],
            value=":".join(parts[1:]),
            lang=lang,
            type_name=self.tag_names[parts[0]]["names"][lang],
            value_name=self.tag_names[parts[0]]["values"][parts[1]][lang],
        )

    def prepare_concepts(self):
        for concept in Concept.objects.all().prefetch_related("tags"):
            self.concepts["{}-{}".format(concept.identifier, concept.lang)] = concept

    def process_concepts(self, concepts, action_names, tags):
        Concept.objects.all().update(active=False)
        for concept in concepts:
            for lang, name in concept["names"].items():
                key = "{}-{}".format(Concept.create_identifier(concept["query"]), lang)
                if key in self.concepts:
                    db_concept = self.concepts[key]
                else:
                    db_concept = Concept(query=concept["query"], lang=lang)
                db_concept.name = concept["names"][lang]
                db_concept.active = True
                db_concept.save()

                # handle tags
                for tag in concept["tags"]:
                    if tag + ":" + lang not in self.tags:
                        self.add_tag(tag, lang)
                new_tags = set([self.tags[t + ":" + lang] for t in concept["tags"]])
                for tag in new_tags - set(db_concept.tags.all()):
                    db_concept.tags.add(tag)
                for tag in set(db_concept.tags.all()) - new_tags:
                    db_concept.tags.remove(tag)

                # handle actions
                for identifier, urls in concept["actions"].items():
                    action, created = Action.objects.get_or_create(concept=db_concept, identifier=identifier)
                    action.url = urls[lang]
                    action.name = action_names[identifier][lang]
                    action.save()
                db_concept.actions.all().exclude(identifier__in=concept["actions"]).delete()
