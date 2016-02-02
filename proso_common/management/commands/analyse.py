from optparse import make_option
import gc
from time import time
import importlib

import os
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings


INPUT_DIR = settings.DATA_DIR
OUTPUT_DIR = os.path.join(settings.MEDIA_ROOT, "analysis")


class Command(BaseCommand):

    help = 'Create analysis - graphs etc.'

    option_list = BaseCommand.option_list + (
        make_option(
            '--no-dump',
            dest='dump_data',
            default=True,
            action="store_false",
            help='Do not dump data to csv and use existing ones.'),
    )

    def __init__(self):
        super(Command, self).__init__()
        self.modules = []
        self.output_dirs = {}

    def handle(self, *args, **options):
        if options["dump_data"]:
            call_command("table2csv")
        self._find_apps_to_analyse()
        self._analyse()

    def _find_apps_to_analyse(self):
        for app in settings.INSTALLED_APPS:
            try:
                module = importlib.import_module("{}.analysis".format(app))
                self.modules.append(module)
                dir = self.output_dirs[module] = os.path.join(OUTPUT_DIR, app)
                if not os.path.exists(dir):
                    os.makedirs(dir)
            except ImportError:
                pass

    def _prepare_dataset(self, module, dataset):
        t = time()
        df = dataset(INPUT_DIR)
        self.stdout.write("  {} - {:.4}s".format(dataset.__name__, time() - t))
        return df

    def _analyse(self):
        for module in self.modules:
            self.stdout.write("{}:".format(module.__name__))
            for dataset, analysis in list(module.DS2A_MAP.items()):
                df = self._prepare_dataset(module, dataset)
                for analyse in analysis:
                    t = time()
                    fig = analyse(df)
                    if fig is None:
                        continue
                    fig.tight_layout()
                    fig.savefig(os.path.join(self.output_dirs[module], "{}.png".format(analyse.__name__)))
                    self.stdout.write("     - {} - {:.4}s".format(analyse.__name__, time() - t))

                del df
                gc.collect()
