from django.conf import settings
from django.core.management.base import BaseCommand
from proso_common.models import CustomConfig
import os.path
import yaml
from django.db import transaction
from optparse import make_option


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option(
            '-f',
            '--file',
            dest='filename',
            default=os.path.join(settings.BASE_DIR, 'proso_custom_config.yaml')
        ),
    )

    def handle(self, *args, **options):
        with transaction.atomic():
            CustomConfig.objects.filter(user_id=None).delete()
            with open(options['filename'], 'r', encoding='utf8') as f:
                for app_name, keys in yaml.load(f).items():
                    for key, records in keys.items():
                        for record in records:
                            CustomConfig.objects.try_create(
                                app_name,
                                key,
                                record['value'],
                                user_id=None,
                                condition_key=record['condition_key'],
                                condition_value=record['condition_value']
                            )
