from collections import defaultdict
from contextlib import closing
from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from proso.django.config import get_config as get_config_original, get_global_config as get_global_config_original, override_value, instantiate_from_json
from proso.django.request import is_user_id_overridden, is_time_overridden, get_user_id
from proso.django.response import BadRequestException
from proso.func import function_name
from threading import currentThread
from proso.events.client import EventsLogger, Pusher, EventClient
import logging
import abc
import hashlib
import importlib
import json
import os
import datetime

_is_user_overriden_from_url = {}
_is_time_overriden_from_url = {}

_custom_configs = {}
_custom_config_filters = {}


class ProsoEventsLogger(EventsLogger):
    def emit(self, event_type: str, data: dict, tags: list = [], time: datetime.datetime = datetime.datetime.now()):
        try:
            super().emit(event_type, data, tags, time)
        except:
            logging.getLogger('django.request').error('Wrong configuration of proso-events. Events are dropped.')


def get_events_logger(events_log_name=None):
    return ProsoEventsLogger(
        get_config('proso_common', 'events.db_file', default=os.path.join(settings.DATA_DIR, events_log_name if events_log_name else 'events.log')),
        get_config('proso_common', 'events.source_name', default='default')
    )


def get_events_client():
    return EventClient(
        get_config('proso_common', 'events.token', required=True),
        get_config('proso_common', 'events.endpoint', required=True),
        get_config('proso_common', 'events.source_name', required=True)
    )


def get_events_pusher(events_log_name=None):
    return Pusher(get_events_client(), (get_events_logger(events_log_name)).event_file)


def reset_custom_configs():
    global _custom_configs
    _custom_configs[currentThread()] = None


def reset_custom_config_filters():
    global _custom_config_filters
    _custom_config_filters[currentThread()] = {}


def reset_url_overridden():
    global _is_user_overriden_from_url
    global _is_time_overriden_from_url
    _is_user_overriden_from_url[currentThread()] = False
    _is_time_overriden_from_url[currentThread()] = False


def add_custom_config_filter(config_filter):
    global _custom_config_filters
    _custom_config_filters[currentThread()][function_name(config_filter)] = config_filter


def current_custom_configs():
    result = []
    global _custom_configs
    global _custom_config_filters
    if _custom_configs.get(currentThread()) is None:
        user_id = get_user_id()
        if user_id is not None:
            _custom_configs[currentThread()] = CustomConfig.objects.current_custom_configs(user_id)

    def _filter_config(config):
        c_key, c_value = next(iter(config['condition'].items()))
        if c_key is None:
            return True
        all_nones = True
        for config_filter in _custom_config_filters[currentThread()].values():
            filter_result = config_filter(c_key, c_value)
            if filter_result is not None:
                all_nones = False
                if not filter_result:
                    return False
        return not all_nones

    customs = _custom_configs.get(currentThread())
    if customs is not None:
        for key, configs in customs.items():
            valid_configs = [c for c in configs if _filter_config(c)]
            if len(valid_configs):
                result.append((key, valid_configs[0]['content']))
    return result


def get_global_config(config_name=None):
    original_config = get_global_config_original(config_name)
    for key, value in current_custom_configs():
        original_config = override_value(None, original_config, key, value)
    return original_config


def get_config(app_name, key, config_name=None, required=False, default=None):
    config = get_global_config(config_name).get(app_name)
    keys = key.split('.')
    for k in keys:
        if config is None:
            break
        config = config.get(k)
    if config is None:
        config = os.getenv('{}.{}'.format(app_name, key).replace('.', '_').upper())
    if config is None:
        if required:
            raise Exception("There is no key [%s] in configuration [%s] and app [%s]" % (key, config_name, app_name))
        return default
    return config


def instantiate_from_config(app_name, key, default_class=None, default_parameters=None, pass_parameters=None, config_name=None):
    config = get_config(app_name, key, config_name=config_name, required=(default_class is None), default={})
    return instantiate_from_json(
        config,
        default_class=default_class,
        default_parameters=default_parameters,
        pass_parameters=pass_parameters
    )


def instantiate_from_config_list(app_name, key, pass_parameters=None, config_name=None):
    configs = get_config(app_name, key, config_name=config_name, default=[])
    return [
        instantiate_from_json(config, pass_parameters=pass_parameters)
        for config in configs
    ]


class CommonMiddleware(object):
    def process_request(self, request):
        reset_url_overridden()
        global _is_user_overriden_from_url
        global _is_time_overriden_from_url
        _is_user_overriden_from_url[currentThread()] = is_user_id_overridden(request)
        _is_time_overriden_from_url[currentThread()] = is_time_overridden(request)
        reset_custom_configs()
        reset_custom_config_filters()


def get_content_hash(content):
    return hashlib.sha1(content.encode()).hexdigest()


def get_custom_exports():
    result = {}
    for app in settings.INSTALLED_APPS:
        try:
            app_models = importlib.import_module('%s.models' % app)
            if not hasattr(app_models, 'PROSO_CUSTOM_EXPORT'):
                continue
            result[app] = {'custom_{}_{}'.format(app, name): sql for (name, sql) in app_models.PROSO_CUSTOM_EXPORT.items()}
        except ImportError:
            continue
    return result


def get_tables_allowed_to_export():
    tables = {}
    for app in settings.INSTALLED_APPS:
        try:
            app_models = importlib.import_module('%s.models' % app)
            if not hasattr(app_models, 'PROSO_MODELS_TO_EXPORT'):
                continue
            tables[app] = [(model._meta.pk.column, model._meta.db_table) for model in app_models.PROSO_MODELS_TO_EXPORT]
        except ImportError:
            continue
    return tables


def get_integrity_checks():
    checks = []
    for app in settings.INSTALLED_APPS:
        try:
            app_models = importlib.import_module('%s.models' % app)
            if not hasattr(app_models, 'PROSO_INTEGRITY_CHECKS'):
                continue
            checks += [check_class() for check_class in app_models.PROSO_INTEGRITY_CHECKS]
        except ImportError:
            continue
    return checks


class IntegrityCheck:

    def get_seed(self):
        return self._seed

    def set_seed(self, seed):
        self._seed = seed

    @abc.abstractmethod
    def check(self):
        """
        Perform integrity check

        Returns:
            None if everything is OK, message (dict) otherwise
        """
        pass


class ConfigManager(models.Manager):

    def from_content(self, content, app_name=None, key=None):
        try:
            content = json.dumps(content, sort_keys=True)
            content_hash = get_content_hash(content)
            return self.get(content_hash=content_hash, app_name=app_name, key=key)
        except Config.DoesNotExist:
            config = Config(
                app_name=app_name,
                key=key,
                content=content,
                content_hash=content_hash)
            config.save()
            return config


class Config(models.Model):

    app_name = models.CharField(max_length=100, null=True, blank=True)
    key = models.CharField(max_length=100, null=True, blank=True)
    content = models.TextField(null=False, blank=False)
    content_hash = models.CharField(max_length=40, null=False, blank=False, db_index=True)

    objects = ConfigManager()

    def to_json(self, nested=False):
        return {
            'id': self.id,
            'object_type': 'config',
            'content': json.loads(self.content),
            'key': self.key,
            'app_name': self.app_name,
        }


class CustomConfigManager(models.Manager):

    def try_create(self, app_name, key, value, user_id, condition_key=None, condition_value=None):
        if not get_config_original('proso_common', 'config.is_custom_config_allowed', default=False):
            raise BadRequestException('Custom configuration is not allowed.')
        if value is None:
            raise Exception("The value can not be None.")
        if isinstance(value, dict) or isinstance(value, list):
            raise Exception("The value has to be scalar.")
        if isinstance(value, str):
            if value.isdigit():
                value = int(value)
            elif value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.replace('.', '').isdigit():
                value = float(value)
        config = Config.objects.from_content(value, key=key, app_name=app_name)
        created = self.create(
            user_id=user_id,
            condition_key=condition_key,
            condition_value=condition_value,
            config=config
        )
        reset_custom_configs()
        return created

    def current_custom_configs(self, user_id):
        if user_id is None:
            return {}
        if not get_config_original('proso_common', 'config.is_custom_config_allowed', default=False):
            return {}
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT
                    custom_config.id,
                    config.app_name,
                    config.key,
                    config.content,
                    condition_key,
                    condition_value
                FROM proso_common_customconfig AS custom_config
                INNER JOIN proso_common_config AS config ON config.id = custom_config.config_id
                WHERE custom_config.id IN (
                    SELECT MAX(custom_config.id)
                    FROM proso_common_customconfig as custom_config
                    INNER JOIN proso_common_config AS config ON config.id = custom_config.config_id
                    WHERE user_id = %s
                    GROUP BY config.app_name, config.key, condition_key, condition_value
                )
                ORDER BY custom_config.id DESC
                ''', [user_id])
            result = defaultdict(list)
            for pk, app_name, key, content, condition_key, condition_value in cursor:
                result['{}.{}'.format(app_name, key)].append({
                    'pk': pk,
                    'content': json.loads(content),
                    'condition': {condition_key: condition_value}
                })
            return result


class CustomConfig(models.Model):

    config = models.ForeignKey(Config)
    user = models.ForeignKey(User)
    condition_key = models.CharField(max_length=255, null=True, blank=True, default=None)
    condition_value = models.TextField(null=True, blank=True, default=None)

    objects = CustomConfigManager()


@receiver(pre_save)
def check_user_or_time_overridden(sender, instance, **kwargs):
    instance_class = '{}.{}'.format(instance.__class__.__module__, instance.__class__.__name__)
    if instance_class.endswith('Session') or instance_class.endswith('UserStat'):
        return
    if _is_user_overriden_from_url.get(currentThread(), False):
        raise BadRequestException("Nothing ({}) can be saved when the user is overridden from URL.".format(instance_class))
    if _is_time_overriden_from_url.get(currentThread(), False):
        raise BadRequestException("Nothing ({}) can be saved when the time is overridden from URL.".format(instance_class))
