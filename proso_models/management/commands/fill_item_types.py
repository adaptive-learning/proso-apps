from contextlib import closing
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import connection
from proso_models.models import ItemType


class Command(BaseCommand):

    def handle(self, *args, **options):
        with closing(connection.cursor()) as cursor:
            cursor.execute('''
                UPDATE proso_models_item
                SET item_type_id = NULL
                ''')
        for item_type in ItemType.objects.filter(valid=True):
            with closing(connection.cursor()) as cursor:
                cursor.execute('''
                    UPDATE proso_models_item
                    SET item_type_id = {}
                    WHERE id IN (SELECT DISTINCT({}) FROM {})
                '''.format(item_type.id, item_type.foreign_key, item_type.table))
        cache.clear()
