from django.conf import settings
from threading import currentThread
import json
import yaml
import proso.util


_config_name = {}
_config = {}


def set_default_config_name(config_name):
    _config_name[currentThread()] = config_name


def get_default_config_name():
    return _config_name.get(currentThread(), settings.PROSO_CONFIG.get('default', 'default'))


def get_subconfig(app_name, key, config_name=None, required=False, default=None):
    if default is None:
        default = {}
    if config_name is None:
        config_name = get_default_config_name()
    subconfig = get_config(app_name, config_name=config_name).get(key)
    if subconfig is None:
        if required:
            raise Exception("There is no key [%s] in configuration [%s] and app [%s]" % (key, config_name, app_name))
        return default
    return subconfig


def instantiate_from_subconfig(app_name, key, default_class=None, default_parameters=None, pass_parameters=None, config_name=None):
    if pass_parameters is None:
        pass_parameters = []
    config = get_subconfig(app_name, key, config_name=config_name, required=(default_class is None))
    return proso.util.instantiate(
        config.get('class', default_class),
        *pass_parameters,
        **config.get('parameters', default_parameters if default_parameters else {})
    )


def get_config(app_name, config_name=None):
    return get_global_config(config_name).get(app_name, {})


def get_global_config(config_name=None):
    if config_name is None:
        config_name = get_default_config_name()
    return _load_config().get(config_name, {})


def _load_config():
    if currentThread() not in _config:
        config_path = settings.PROSO_CONFIG['path']
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

