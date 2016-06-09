from django.core.management.base import BaseCommand
from proso_common.models import get_integrity_checks
from django.conf import settings
from optparse import make_option
import logging
import random
import json
import sys


LOGGER = logging.getLogger('proso.internal')


class Command(BaseCommand):
    help = "Perform integrity checks"
    option_list = BaseCommand.option_list + (
        make_option(
            '--seed',
            type=int,
            default=None
        ),
    )

    def handle(self, *args, **options):
        if options['seed'] is None:
            seed = random.randint(1, 10 ** 10)
        else:
            seed = options['seed']
        failed = {}
        for integrity_check in get_integrity_checks():
            random.seed(seed)
            integrity_check.set_seed(seed)
            result = integrity_check.check()
            if result is not None:
                failed[_check_name(integrity_check)] = result
                print('FAILED:', _check_name(integrity_check))
            else:
                print('PASSED:', _check_name(integrity_check))
        if len(failed) > 0:
            dest_file = '{}/integrity_check_{}.txt'.format(settings.DATA_DIR, seed)
            print('REPORT:', dest_file)
            with open(dest_file, 'w') as f:
                f.write(json.dumps({'failed_checks': failed}, sort_keys=True, indent=4))
            message = 'The integrity check failed, seed: {}'.format(seed)
            LOGGER.error(message)
            sys.exit(message)


def _check_name(integrity_check):
    return '{}.{}'.format(integrity_check.__class__.__module__, integrity_check.__class__.__name__)
