from django.conf import settings
from django.db import models
import hashlib
import importlib
import json


def get_content_hash(content):
    return hashlib.sha1(content).hexdigest()


def get_tables_allowed_to_export():
    tables = []
    for app in settings.INSTALLED_APPS:
        try:
            app_models = importlib.import_module('%s.models' % app)
            if not hasattr(app_models, 'PROSO_MODELS_TO_EXPORT'):
                continue
            tables += map(lambda model: model._meta.db_table, app_models.PROSO_MODELS_TO_EXPORT)
        except ImportError:
            continue
    return tables


class ConfigManager(models.Manager):

    def from_content(self, content, app_name=None, key=None):
        try:
            content = json.dumps(content)
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
