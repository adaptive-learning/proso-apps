from django.core.management.base import BaseCommand, CommandError
from jsonschema import validate
from proso_configab.models import Experiment, Variable, PossibleValue, ExperimentSetup
from datetime import datetime
from django.db import transaction
import os
import json


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('filename')

    def handle(self, *args, **options):
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "experiments_schema.json"), "r", encoding='utf8') as schema_file:
            schema = json.load(schema_file)
        with open(options['filename'], 'r', encoding='utf8') as json_file:
            with transaction.atomic():
                data = json.load(json_file)
                validate(data, schema)
                self._load_experiments(data["experiments"])

    def _load_experiments(self, data):
        for experiment in data:
            experiment_db, created = Experiment.objects.get_or_create(identifier=experiment['id'])
            if 'paused' in experiment and experiment['paused'] != experiment_db.is_paused:
                experiment_db.is_paused = experiment['paused']
                experiment_db.save()
                print(' -- experiment', experiment['id'], ('paused' if experiment['paused'] else 'unpaused'))
            if 'disabled' in experiment:
                if not experiment_db.is_enabled:
                    if not experiment['disabled']:
                        raise CommandError('Experiment "{}" can not be enabled again.'.format(experiment['id']))
                elif experiment['disabled']:
                    experiment_db.is_enabled = False
                    experiment_db.time_disabled = datetime.now()
                    experiment_db.save()
                    print(' -- experiment', experiment['id'], 'disabled')
            if not created:
                print(' -- experiment', experiment['id'], 'already created, skipping')
                continue
            if 'variables' in experiment and 'setups' in experiment:
                raise CommandError('The experiment ({}) can not contain both variables and setups.'.format(experiment['id']))
            if 'variables' in experiment:
                self._load_variables(experiment_db, experiment['variables'])
            elif 'setups' in experiment:
                self._load_setups(experiment_db, experiment['setups'])
            else:
                raise CommandError('The experiment ({}) has to contain either variables, or setups.'.format(experiment['id']))
            print(' -- experiment', experiment['id'], 'created')

    def _load_variables(self, experiment, variables_json):
        values_list_with_probabilities = []
        for variable in variables_json:
            variable_db, _ = Variable.objects.get_or_create(app_name=variable['app_name'], name=variable['name'])
            prob_sum = sum([val['probability'] for val in variable['values']])
            if prob_sum != 100:
                raise CommandError('The total sum of probs for variable "{}.{}" is {}, expected 100'.format(variable['app_name'], variable['name'], prob_sum))
            values_with_probs = []
            for value in variable['values']:
                value_db, _ = PossibleValue.objects.get_or_create(
                    variable=variable_db,
                    value=value['value'],
                )
                values_with_probs.append((value_db, value['probability']))
            values_list_with_probabilities.append(values_with_probs)
        ExperimentSetup.objects.from_values_product(experiment, values_list_with_probabilities)

    def _load_setups(self, experiment, setups_json):
        total_prob = sum([s['probability'] for s in setups_json])
        if total_prob != 100:
            raise CommandError('The total sum of probs for setups in experiment {} is {}, expected 100.'.format(experiment.identifier, total_prob))
        for setup in setups_json:
            values = []
            for variable in setup['variables']:
                variable_db, _ = Variable.objects.get_or_create(app_name=variable['app_name'], name=variable['name'])
                value_db, _ = PossibleValue.objects.get_or_create(
                    variable=variable_db,
                    value=variable['value'],
                )
                values.append(value_db)
            ExperimentSetup.objects.from_values(experiment, values, setup['probability'])
