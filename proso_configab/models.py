from collections import defaultdict
from contextlib import closing
from datetime import datetime
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db import connection
from django.db import models
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from functools import reduce
from itertools import product
from proso.django.config import override
from proso.django.models import disable_for_loaddata
from proso.list import group_by
from proso_common.models import instantiate_from_config
from proso_models.models import Answer, learning_curve, survival_curve_answers, survival_curve_time
import hashlib
import json
import logging


LOGGER = logging.getLogger('django.request')


def get_assignment_strategy():
    return instantiate_from_config(
        'proso_configab', 'assignment_strategy',
        default_class='proso_configab.assignment.RandomStrategy'
    )


class ABConfigMiddleware(object):
    def process_request(self, request):
        if request.user is None or request.user.id is None:
            LOGGER.debug('There is no user to setup configuration based on AB experiments in middleware.')
            return
        LOGGER.debug('Setting up configuration for user {} based on AB experiments in middleware.'.format(request.user.id))
        for app_name_key, value in UserSetup.objects.get_variables_to_override(request.user.id).items():
            LOGGER.debug('Setting {} to "{}" for user {}.'.format(app_name_key, value, request.user.id))
            override(app_name_key, value)


class Experiment(models.Model):

    identifier = models.CharField(max_length=100, unique=True)
    is_enabled = models.BooleanField(default=True)
    is_paused = models.BooleanField(default=False)
    time_disabled = models.DateTimeField(default=None, null=True, blank=True)
    time_created = models.DateTimeField(default=datetime.now)

    def to_json(self, nested=False):
        result = {
            'object_type': 'configab_experiment',
            'id': self.id,
            'identifier': self.identifier,
            'is_enabled': self.is_enabled,
            'is_paused': self.is_paused,
            'time_created': self.time_created.strftime('%Y-%m-%d %H:%M:%S'),
        }
        if not self.is_enabled:
            result['time_disabled'] = self.time_disabled.strftime('%Y-%m-%d %H:%M:%S')
        if not nested:
            result['setups'] = [setup.to_json(nested=True) for setup in self.experimentsetup_set.all()]
        return result


class Variable(models.Model):

    app_name = models.CharField(max_length=100)
    name = models.CharField(max_length=100)

    def to_json(self, nested=False):
        return {
            'object_type': 'configab_variable',
            'app_name': self.app_name,
            'name': self.name,
            'id': self.id,
        }


class PossibleValue(models.Model):

    value = models.CharField(max_length=100)
    variable = models.ForeignKey(Variable)

    class Meta:
        unique_together = ('variable', 'value')

    def to_json(self, nested=False):
        result = {
            'object_type': 'configab_possible_value',
            'id': self.id,
            'value': self.value,
        }
        result['variable'] = self.variable.to_json(nested=True)
        if nested:
            result['variable_id'] = self.variable_id
        else:
            result['experiment'] = self.experiment.to_json(nested=True)
        return result


class ExperimentSetupManager(models.Manager):

    def get_stats(self, experiment_setup_ids, survival_curve_length=100, learning_curve_length=5, curve_max_users=1000):
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT
                    proso_configab_answerexperimentsetup.experiment_setup_id,
                    proso_models_answer.user_id
                FROM proso_models_answer
                INNER JOIN proso_configab_answerexperimentsetup ON proso_configab_answerexperimentsetup.answer_id = proso_models_answer.id
                WHERE proso_configab_answerexperimentsetup.experiment_setup_id IN (''' + ', '.join(['%s' for _ in experiment_setup_ids]) + ''')
                GROUP BY proso_configab_answerexperimentsetup.experiment_setup_id, proso_models_answer.user_id
                ''',
                experiment_setup_ids
            )
            experiment_users = defaultdict(set)
            for row in cursor:
                experiment_users[row[0]].add(row[1])
            result = {}
            for experiment_setup_id in experiment_setup_ids:
                if experiment_setup_id in experiment_users:
                    users = experiment_users[experiment_setup_id]
                    result[experiment_setup_id] = {
                        'number_of_users': len(users),
                        'survival_curve_answers': survival_curve_answers(survival_curve_length, users=users, number_of_users=curve_max_users),
                        'survival_curve_time': survival_curve_time(survival_curve_length * 6, users=users, number_of_users=curve_max_users),
                        'learning_curve': learning_curve(learning_curve_length, users=users, number_of_users=curve_max_users),
                    }
                else:
                    result[experiment_setup_id] = {
                        'number_of_users': 0,
                        'survival_curve_answers': survival_curve_answers(survival_curve_length, users=[], number_of_users=curve_max_users),
                        'survival_curve_time': survival_curve_time(survival_curve_length * 6, users=[], number_of_users=curve_max_users),
                        'learning_curve': learning_curve(learning_curve_length, users=[], number_of_users=curve_max_users),
                    }
            return result

    def from_values(self, experiment, values, probability):
        content_hash = hashlib.sha1(
            json.dumps(
                {'{}'.format(val.variable.id): val.id for val in values},
                sort_keys=True
            ).encode()
        ).hexdigest()
        setup, created = self.get_or_create(content_hash=content_hash, experiment_id=experiment.id)
        if created:
            setup.probability = probability
            for val in values:
                setup.values.add(val)
            setup.save()
        return setup

    def from_values_product(self, experiment, values_list_with_probabilities):
        result = []
        total_probability = sum([
            reduce(lambda x, y: x * y, [p / 100 for _, p in pvals])
            for pvals in product(*values_list_with_probabilities)
        ])
        for pvalues in product(*values_list_with_probabilities):
            setup_probability = 100 * reduce(lambda x, y: x * y, [p / 100 for _, p in pvalues]) / (total_probability if total_probability > 0 else 1)
            result.append(self.from_values(experiment, [v for v, _ in pvalues], setup_probability))
        return result


class ExperimentSetup(models.Model):

    experiment = models.ForeignKey(Experiment, null=True, blank=True)
    content_hash = models.CharField(max_length=40)
    values = models.ManyToManyField(PossibleValue)
    probability = models.FloatField(null=True, blank=True, default=0)

    class Meta:
        unique_together = ('content_hash', 'experiment')

    objects = ExperimentSetupManager()

    def to_json(self, nested=False):
        result = {
            'object_type': 'configab_experiment_setup',
            'id': self.id,
            'content_hash': self.content_hash,
            'values': [val.to_json(nested=True) for val in self.values.all()],
            'probability': self.probability,
        }
        if nested:
            result['experiment_id'] = self.experiment_id
        else:
            result['experiment'] = self.experiment.to_json(nested=True)
        return result


class UserSetupManager(models.Manager):

    def get_variables_to_override(self, user_id):
        # Paused experiments have effect on already assigned users, but new
        # users are not assigned.
        with transaction.atomic():
            assigned_setups = list(ExperimentSetup.objects.prefetch_related('values').filter(usersetup__user_id=user_id, experiment__is_enabled=True))
            assigned_experiments = {s.experiment_id for s in assigned_setups}
            if Answer.objects.filter(user_id=user_id).count() == 0:
                setups_by_experiment = group_by(
                    ExperimentSetup.objects.prefetch_related('values').filter(experiment__is_enabled=True, experiment__is_paused=False),
                    by=lambda s: s.experiment_id
                )
                to_assign = get_assignment_strategy().assign_setups(
                    user_id,
                    {e: setups for e, setups in setups_by_experiment.items() if e not in assigned_experiments}
                )
                for setup in to_assign:
                    assigned_setups.append(setup)
                    UserSetup.objects.create(
                        user_id=user_id,
                        experiment_setup=setup
                    )
            return {
                '{}.{}'.format(val.variable.app_name, val.variable.name): val.value
                for setup in assigned_setups
                for val in setup.values.all()
            }


class UserSetup(models.Model):

    experiment_setup = models.ForeignKey(ExperimentSetup)
    user = models.OneToOneField(User)

    objects = UserSetupManager()

    def to_json(self, nested=False):
        result = {
            'object_type': 'configab_user_setup',
            'id': self.id,
            'user_id': self.user_id,
        }
        if nested:
            result['experiment_setup_id'] = self.experiment_setup_id
        else:
            result['experiment_setup'] = self.experiment_setup.to_json(nested=True)
        return result


class AnswerExperimentSetup(models.Model):

    experiment_setup = models.ForeignKey(ExperimentSetup)
    answer = models.ForeignKey(Answer)


@receiver(user_logged_in)
def setup_config(sender, user, request, **kwargs):
    for app_name_key, value in UserSetup.objects.get_variables_to_override(user.id).items():
        override(app_name_key, value)
    LOGGER.debug('Setting up configuration for user {} based on AB experiments in login signal reciever.'.format(user.id))


@receiver(post_save)
@disable_for_loaddata
def save_answer_experiment_setup(sender, instance, **kwargs):
    if not issubclass(sender, Answer) or not kwargs['created']:
        return
    setups = UserSetup.objects.filter(user_id=instance.user_id, experiment_setup__experiment__is_enabled=True)
    if len(setups) == 1:
        AnswerExperimentSetup.objects.create(
            experiment_setup_id=setups[0].experiment_setup_id,
            answer_id=instance.id)
