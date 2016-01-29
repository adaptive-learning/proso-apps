from django.conf import settings
from django.db import models
import datetime
import random
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
import logging
from threading import currentThread

_request_cache = {}
_request_cache_initialized = False


LOGGER = logging.getLogger(__name__)


class ABMiddleware:

    def process_request(self, request):
        Experiment.objects.init_request(request)


class ExperimentManager(models.Manager):

    def init_request(self, request):
        user = getattr(request, 'user', None)
        if user is None or user.is_anonymous():
            self.clear_session(request.session)
            self._init_request_cache(request)
            return
        if 'ab_experiment_values_modified' in request.session:
            if user.id is None:
                self.clear_session(request.session)
            if user.id != request.session.get('ab_experiment_values_user'):
                self.clear_session(request.session)
            if 'ab_experiment_reset' in request.GET:
                self.clear_session(request.session)
        override = {}
        if user.is_staff:
            for key, value in list(request.GET.items()):
                if key.startswith('ab_value_'):
                    override[key.replace('ab_value_', '')] = value
        if 'ab_experiment_values_modified' in request.session:
            saved_time = datetime.datetime.strptime(
                request.session['ab_experiment_values_modified'], '%Y-%m-%d %H:%M:%S')
            if (datetime.datetime.now() - saved_time).total_seconds() < 15 * 60:
                self._init_request_cache(request)
                return
        if 'ab_experiment_values' not in request.session:
            request.session['ab_experiment_values'] = {}
            request.session['ab_experiment_values_user'] = user.id
        request.session['ab_experiment_values_modified'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for k, v in override.items():
            request.session['ab_experiment_values'][k] = v
        for name, value in UserValue.objects.for_user(user).items():
            if name in override:
                continue
            request.session['ab_experiment_values'][name] = value
        LOGGER.debug('initialized AB experiments for user %s: %s' % (str(user.id), str(request.session.get('ab_experiment_values', []))))
        self._init_request_cache(request)
        return request

    def clear_session(self, session):
        if 'ab_experiment_values' in session:
            del session['ab_experiment_values']
        if 'ab_experiment_values_modified' in session:
            del session['ab_experiment_values_modified']
        if 'ab_experiment_values_user' in session:
            del session['ab_experiment_values_user']

    def new_experiment(self, name, values, default_value, active=True):
        total_prob = sum([probability for (probability, value) in values])
        if total_prob != 100:
            raise Exception('Total probability has to be equal to 100, it was ' + str(total_prob))
        if default_value not in [p_v[1] for p_v in values]:
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

    def get_values(self, force=True):
        if not force and not _request_cache_initialized:
            return []
        assert _request_cache_initialized, 'ABMiddleware is not loaded'
        return _request_cache.get(currentThread(), [])

    def _init_request_cache(self, request):
        user = getattr(request, 'user', None)
        global _request_cache_initialized
        _request_cache_initialized = True
        _request_cache[currentThread()] = list(Value.objects.filter(
            id__in=[d['id'] for d in list(request.session.get('ab_experiment_values', {}).values())]))
        LOGGER.debug('initialized request cache for AB experiments, user %s' % (str(None if user is None else user.id)))


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
    is_default = models.BooleanField(default=False)

    objects = ValueManager()

    class Meta:
        app_label = 'proso_ab'

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
        if user is None or user.id is None:
            raise Exception('user or user.id is None')
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
                UserValue(user_id=user.id, value=value).save()
                prepared[experiment.name] = value.to_json()
        for experiment, default in defaults.items():
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


@receiver(user_logged_in)
def initialize_request(sender, **kwargs):
    Experiment.objects.init_request(kwargs['request'])


PROSO_MODELS_TO_EXPORT = [Experiment, UserValue, Value]
