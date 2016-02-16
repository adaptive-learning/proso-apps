from proso_models.models import ItemType
from django.core.management.base import BaseCommand
from optparse import make_option


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option(
            '--dry',
            dest='dry',
            action='store_true',
            default=False),
    )

    def handle(self, *args, **options):
        found = []
        for model, table, foreign_key, language in ItemType.objects.find_object_types():
            if not options['dry']:
                found.append(ItemType.objects.get_or_create(
                    model=model,
                    table=table,
                    foreign_key=foreign_key,
                    language=language
                )[0].id)
            print(' - ', model, ':', table, ':', foreign_key, ':', language)
        if not options['dry']:
            valids = ItemType.objects.filter(id__in=found).update(valid=True)
            invalids = ItemType.objects.exclude(id__in=found).update(valid=False)
            print('After database updated: {} valid item types and {} invalid ones.'.format(valids, invalids))
