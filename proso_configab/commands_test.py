from django.core.management import call_command
from django.test import TestCase
from proso_configab.models import Experiment


class TeadExperimentsLoading(TestCase):

    def test_load_configab_experiments(self):
        call_command('load_configab_experiments', 'testproject/test_data/configab/ab_experiments.json')
        self.assertEqual(Experiment.objects.get(is_enabled=True).identifier, 'options-construction')
