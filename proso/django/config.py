from collections import defaultdict
from django.conf import settings
from threading import currentThread
import copy
import json
import os
import proso.reflection
import yaml


DEFAULT_DEFAULT = 'default'
DEFAULT_PATH = os.path.join(settings.BASE_DIR, 'proso_config.yaml')

_config_name = {}
_config = {}
_overridden = defaultdict(dict)
_is_overriden_from_url = {}


class ConfigMiddleware(object):
    def process_request(self, request):
        reset_overridden()
        if not request.user.is_staff:
            return
        for key, value in request.GET.items():
            if key.startswith('config.'):
                _is_overriden_from_url[currentThread()] = True
                key = key.replace('config.', '')
                override(key, value)


def override(app_name_key, value):
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
    _overridden[currentThread()][app_name_key] = value


def is_overridden_from_url():
    return _is_overriden_from_url.get(currentThread(), False)


def reset_overridden():
    global _overridden
    global _is_overriden_from_url
    _overridden[currentThread()] = {}
    _is_overriden_from_url[currentThread()] = False


def is_any_overridden():
    return len(_overridden[currentThread()]) > 0


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


def instantiate_from_json(json, default_class=None, default_parameters=None, pass_parameters=None):
    if pass_parameters is None:
        pass_parameters = []
    return proso.reflection.instantiate(
        json.get('class', default_class),
        *pass_parameters,
        **json.get('parameters', default_parameters if default_parameters else {})
    )


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


def get_global_config(config_name=None):
    if config_name is None:
        config_name = get_default_config_name()
    return _override_value_all(None, None, _load_config().get(config_name, {}))


def _load_config():
    if currentThread() not in _config:
        config_path = get_config_path()
        with open(config_path, 'r', encoding='utf8') as config_data:
            if config_path.endswith('.json'):
                loaded = json.load(config_data, )
            elif config_path.endswith('.yaml'):
                loaded = yaml.load(config_data)
            else:
                raise Exception('There is no support for *.%s files' % config_path.split('.')[-1])
            if settings.DEBUG:
                return loaded
            _config[currentThread()] = loaded
    return _config[currentThread()]


def override_value(app_name_key, value, override_key, override_value):
    if app_name_key is not None and not override_key.startswith(app_name_key):
        return value
    if not isinstance(value, dict):
        if override_key == app_name_key:
            return override_value
        else:
            return value
    if app_name_key == override_key:
        raise Exception("The dict can not be overridden by scalar.")
    if app_name_key is not None:
        override_key = override_key.replace('{}.'.format(app_name_key), '')
    override_keys = override_key.split('.')
    to_override = value
    for k in override_keys[:-1]:
        if k not in to_override:
            to_override[k] = {}
        to_override = to_override[k]
    to_override[override_keys[-1]] = override_value
    return value


def _override_value_all(app_name, key, value):
    if isinstance(value, dict):
        value = copy.deepcopy(value)
    if not is_any_overridden():
        return value
    if app_name is None and key is None:
        app_name_key = None
    else:
        app_name_key = '{}.{}'.format(app_name, key)
    for to_override_key, to_override_value in _overridden[currentThread()].items():
        value = override_value(app_name_key, value, to_override_key, to_override_value)
    return value
