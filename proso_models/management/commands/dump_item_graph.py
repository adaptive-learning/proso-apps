from django.core.management.base import BaseCommand
from optparse import make_option
from proso_models.models import Item
from proso.list import flatten
import json


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option(
            '--root',
            dest='roots',
            action='append',
            default=[]
        ),
        make_option(
            '--lang',
            dest='lang',
            action='store',
            default='en'
        )
    )

    def handle(self, *args, **options):
        if len(options['roots']) == 0:
            raise Exception('At least one root has to be specified.')
        translated_roots = Item.objects.translate_identifiers(options['roots'], options['lang'])
        graph = Item.objects.get_children_graph(list(translated_roots.values()), language=options['lang'])
        translated_items = {
            i: '{}/{}'.format(o['object_type'], o['identifier'])
            for i, o in Item.objects.translate_item_ids(flatten(graph.values()), language=options['lang'], is_nested=True).items()
        }
        translated_graph = {translated_items.get(u): [translated_items.get(v) for v in vs] for u, vs in graph.items()}
        print(json.dumps(translated_graph))
