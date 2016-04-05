from django.conf import settings
from django.db import models
from threading import currentThread
from proso.django.request import is_user_id_overridden, is_time_overridden
from django.dispatch import receiver
from django.db.models.signals import pre_save
from proso.django.response import BadRequestException
import hashlib
import importlib
import json
import abc

_is_user_overriden_from_url = {}
_is_time_overriden_from_url = {}


def reset_url_overridden():
    global _is_user_overriden_from_url
    global _is_time_overriden_from_url
    _is_user_overriden_from_url[currentThread()] = False
    _is_time_overriden_from_url[currentThread()] = False


class CommonMiddleware(object):
    def process_request(self, request):
        reset_url_overridden()
        global _is_user_overriden_from_url
        global _is_time_overriden_from_url
        _is_user_overriden_from_url[currentThread()] = is_user_id_overridden(request)
        _is_time_overriden_from_url[currentThread()] = is_time_overridden(request)


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


@receiver(pre_save)
def check_user_or_time_overridden(sender, instance, **kwargs):
    instance_class = '{}.{}'.format(instance.__class__.__module__, instance.__class__.__name__)
    if instance_class.endswith('Session') or instance_class.endswith('UserStat'):
        return
    if _is_user_overriden_from_url.get(currentThread(), False):
        raise BadRequestException("Nothing ({}) can be saved when the user is overridden from URL.".format(instance_class))
    if _is_time_overriden_from_url.get(currentThread(), False):
        raise BadRequestException("Nothing ({}) can be saved when the time is overridden from URL.".format(instance_class))
