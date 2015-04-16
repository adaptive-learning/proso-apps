from django.conf import settings
from threading import currentThread
import json
import yaml
import proso.util
import os


DEFAULT_DEFAULT = 'default'
DEFAULT_PATH = os.path.join(settings.BASE_DIR, 'proso_config.yaml')

_config_name = {}
_config = {}


def set_default_config_name(config_name):
    _config_name[currentThread()] = config_name


def get_default_config_name():
    if currentThread() in _config_name:
        return _config_name[currentThread()]
    if not hasattr(settings, 'PROSO_CONFIG'):
        return DEFAULT_DEFAULT
    return settings.PROSO_CONFIG.get('default', DEFAULT_DEFAULT)


def get_config_path():
    if not hasattr(settings, 'PROSO_CONFIG'):
        return DEFAULT_PATH
    return settings.PROSO_CONFIG.get('path', DEFAULT_PATH)


def instantiate_from_config(app_name, key, default_class=None, default_parameters=None, pass_parameters=None, config_name=None):
    if pass_parameters is None:
        pass_parameters = []
    config = get_config(app_name, key, config_name=config_name, required=(default_class is None), default={})
    return proso.util.instantiate(
        config.get('class', default_class),
        *pass_parameters,
        **config.get('parameters', default_parameters if default_parameters else {})
    )


def get_config(app_name, key, config_name=None, required=False, default=None):
    config = get_global_config(config_name).get(app_name)
    keys = key.split('.')
    for k in keys:
        if config is None:
            break
        config = config.get(k)
    if config is None:
        if required:
            raise Exception("There is no key [%s] in configuration [%s] and app [%s]" % (key, config_name, app_name))
        return default
    return config


def get_global_config(config_name=None):
    if config_name is None:
        config_name = get_default_config_name()
    return _load_config().get(config_name, {})


def _load_config():
    if currentThread() not in _config:
        config_path = get_config_path()
        with open(config_path, 'r') as config_data:
            if config_path.endswith('.json'):
                loaded = json.load(config_data, 'utf-8')
            elif config_path.endswith('.yaml'):
                loaded = yaml.load(config_data)
            else:
                raise Exception('There is no support for *.%s files' % config_path.split('.')[-1])
            if settings.DEBUG:
                return loaded
            _config[currentThread()] = loaded
    return _config[currentThread()]

