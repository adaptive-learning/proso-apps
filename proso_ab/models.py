from django.conf import settings
from django.db import models
import datetime
import random
from django.contrib.auth.models import User


class ExperimentManager(models.Manager):

    def init_request(self, request):
        if 'ab_experiment_values' in request.session:
            if request.user.id is None:
                del request.session['ab_experiment_values']
            if request.user.id != request.session.get('ab_experiment_values_user'):
                del request.session['ab_experiment_values']
                del request.session['ab_experiment_values_modified']
                del request.session['ab_experiment_values_user']
        override = {}
        if request.user.is_staff:
            if 'ab_experiment_reset' in request.GET:
                del request.session['ab_experiment_values']
                del request.session['ab_experiment_values_modified']
                del request.session['ab_experiment_values_user']
            for key, value in request.GET.items():
                if key.startswith('ab_value_'):
                    override[key.replace('ab_value_', '')] = value
        if 'ab_experiment_values_modified' in request.session:
            saved_time = datetime.datetime.strptime(
                request.session['ab_experiment_values_modified'], '%Y-%m-%d %H:%M:%S')
            if (datetime.datetime.now() - saved_time).total_seconds() < 15 * 60:
                return
        if 'ab_experiment_values' not in request.session:
            request.session['ab_experiment_values'] = {}
            request.session['ab_experiment_values_user'] = request.user.id
        request.session['ab_experiment_values_modified'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for k, v in override.iteritems():
            request.session['ab_experiment_values'][k] = v
        for name, value in UserValue.objects.for_user(request.user).iteritems():
            if name in override:
                continue
            request.session['ab_experiment_values'][name] = value
        return request

    def new_experiment(self, name, values, default_value, active=True):
        total_prob = sum([probability for (probability, value) in values])
        if total_prob != 100:
            raise Exception('Total probability has to be equal to 100, it was ' + str(total_prob))
        if default_value not in map(lambda (p, v): v, values):
            raise Exception('Default value %s is not present in values.' % default_value)
        experiment = Experiment(name=name, active=active)
        experiment.save()
        for probability, value in values:
            Value(
                name=value,
                probability=probability,
                is_default=(default_value==value),
                experiment=experiment).save()

    def get_experiment_value(self, request, experiment_name, default=None):
        for exp, value in request.session.get('ab_experiment_values', {}):
            if exp == experiment_name:
                return value['name']
        return default

    def get_values(self, request):
        return request.session.get('ab_experiment_values', {}).values()


class Experiment(models.Model):

    active = models.BooleanField(default=True)
    name = models.CharField(max_length=100, unique=True)

    objects = ExperimentManager()

    class Meta:
        app_label = 'proso_ab'

    def to_json(self, nested=False):
        return {
            'id': self.id,
            'name': self.name,
            'active': self.active,
            'object_type': 'experiment'
        }


class ValueManager(models.Manager):

    def choose_value(self, experiment):
        values = self.filter(experiment=experiment)
        choice = random.randint(0, 100)
        sum_prob = 0
        for value in values:
            sum_prob += value.probability
            if choice <= sum_prob:
                return value
        raise Exception('should not happen')


class Value(models.Model):

    experiment = models.ForeignKey(Experiment)
    name = models.CharField(max_length=100, unique=True)
    probability = models.IntegerField(default=0)
    is_default = models.BooleanField()

    objects = ValueManager()

    class Meta:
        app_label = 'proso_ab'
        unique_together = ('experiment', 'is_default')

    def to_json(self, nested=False):
        return {
            'id': self.id,
            'name': self.name,
            'default': self.is_default,
            'probability': self.probability,
            'experiment': self.experiment_id if nested else self.experiment.to_json(nested=True),
            'object_type': 'value'
        }


class UserValueManager(models.Manager):

    def for_user(self, user):
        prepared = dict([
            (user_value.value.experiment.name, user_value.value.to_json())
            for user_value in list(self.filter(user_id=user.id).select_related('value__experiment'))
        ])
        defaults = dict([
            (value.experiment.name, value)
            for value in list(Value.objects.filter(is_default=True).select_related('experiment'))
        ])
        experiments = Experiment.objects.filter(active=True)
        for experiment in experiments:
            if experiment.name in prepared:
                continue
            if self.should_be_initialized(user, experiment):
                value = Value.objects.choose_value(experiment)
                UserValue(user=user, value=value).save()
                prepared[experiment.name] = value.to_json()
        for experiment, default in defaults.iteritems():
            if experiment not in prepared:
                prepared[experiment] = default.to_json()
        return prepared

    def should_be_initialized(self, user, experiment):
        if not hasattr(settings, 'PROSO_AB_USER_PREDICATE'):
            return True
        return settings.PROSO_AB_USER_PREDICATE(user)


class UserValue(models.Model):

    user = models.ForeignKey(User)
    value = models.ForeignKey(Value)

    objects = UserValueManager()

    class Meta:
        app_label = 'proso_ab'
