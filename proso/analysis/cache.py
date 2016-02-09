import json
import hashlib
import os
import abc
import pandas
import proso.analysis.config
from functools import wraps
from threading import currentThread

_global_analysis_cache = {}


class abstract_cache_analysis(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def cache_dir(self):
        pass

    @abc.abstractmethod
    def is_active(self):
        pass

    @abc.abstractmethod
    def is_debug(self):
        pass

    @abc.abstractmethod
    def in_memory(self):
        pass

    @abc.abstractmethod
    def override(self):
        pass

    @abc.abstractmethod
    def preprocess_kwargs_for_hash(self, **kwargs):
        pass

    def __call__(self, func):

        @wraps(func)
        def _wrapper(*args, **kwargs):
            global _global_analysis_cache
            if currentThread() not in _global_analysis_cache:
                _global_analysis_cache[currentThread()] = {}
            memory_cache = _global_analysis_cache[currentThread()]
            if '__self__' not in dir(func) and len(args) > 0:
                raise Exception('All arguments have to be key-word.')
            if '__self__' in dir(func) and len(args) > 1:
                raise Exception('All arguments have to be key-word.')
            if '__self__' in dir(func):
                full_func_name = '{}.{}.{}'.format(func.__self__.__class__.__module__, func.__self__.__class__.__name__, func.__func__.__name__)
            else:
                full_func_name =  '{}.{}'.format(func.__module__, func.__name__)
            kwargs_for_hash = self.preprocess_kwargs_for_hash(**dict(kwargs))
            kwargs_hash = hashlib.sha1((full_func_name + json.dumps(kwargs_for_hash, sort_keys=True)).encode()).hexdigest()
            if kwargs_hash in memory_cache:
                return memory_cache[kwargs_hash]
            filename_template = '{}/{}/{}.'.format(self.cache_dir(), full_func_name, kwargs_hash) + '{}'
            if self.is_active() and not self.override() and os.path.exists(filename_template.format('pd')):
                filename = filename_template.format('pd')
                result = pandas.read_pickle(filename)
                if self.is_debug():
                    print('reading cache ({})'.format(len(result)), filename, 'with parameters:')
                    for key, value in sorted(kwargs.items()):
                        print('    - {}: {}'.format(key, value))
                if self.in_memory():
                    memory_cache[kwargs_hash] = result
                return result
            elif self.is_active() and not self.override() and os.path.exists(filename_template.format('json')):
                filename = filename_template.format('json')
                if self.is_debug():
                    print('reading cache', filename, 'with parameters:')
                    for key, value in sorted(kwargs.items()):
                        print('    - {}: {}'.format(key, value))
                with open(filename, 'r') as f:
                    return _convert_json_keys(json.loads(f.read()))
            result = func(*args, **kwargs)
            if not self.is_active():
                return result
            if not os.path.exists('{}/{}'.format(self.cache_dir(), full_func_name)):
                os.makedirs('{}/{}'.format(self.cache_dir(), full_func_name))
            with open(filename_template.format('description.json'), 'w') as f:
                f.write(json.dumps(kwargs_for_hash, sort_keys=True))
            if isinstance(result, dict):
                if self.is_debug():
                    print('writing cache', filename_template.format('json'))
                with open(filename_template.format('json'), 'w') as f:
                    f.write(json.dumps(_jsonify(result), sort_keys=True))
            elif isinstance(result, pandas.DataFrame):
                if self.is_debug():
                    print('writing cache ({})'.format(len(result)), filename_template.format('pd'))
                result.to_pickle(filename_template.format('pd'))
            else:
                raise Exception('The returned type {} is not supported.'.format(type(result)))
            if self.in_memory():
                memory_cache[kwargs_hash] = result
            return result
        return _wrapper


class cache_analysis(abstract_cache_analysis):

    def __init__(self, cache_dir=None, active=None, in_memory=None, override=None):
        self._cache_dir = cache_dir
        self._is_cache_active = active
        self._cache_in_memory = in_memory
        self._override_cache = override

    def cache_dir(self):
        return self._cache_dir if self._cache_dir is not None else \
            proso.analysis.config.load_cache_kwargs().get('cache_dir', 'cache')

    def is_active(self):
        return self._is_cache_active if self._is_cache_active is not None else \
            bool(proso.analysis.config.load_cache_kwargs().get('is_cache_active', True))

    def is_debug(self):
        return True

    def in_memory(self):
        return self._cache_in_memory if self._cache_in_memory is not None else \
             bool(proso.analysis.config.load_cache_kwargs().get('cache_in_memory', True))

    def override(self):
        return self._override_cache if self._override_cache is not None else \
            bool(proso.analysis.config.load_cache_kwargs().get('override_cache', True))

    def preprocess_kwargs_for_hash(self, **kwargs):
        for key, value in proso.analysis.config.load_data_kwargs().items():
            kwargs[key] = value
        return kwargs


def _convert_json_keys(json_struct):
    if isinstance(json_struct, list):
        return list(map(_convert_json_keys, json_struct))
    elif isinstance(json_struct, dict):
        return {_maybe_convert_str(key): _convert_json_keys(val) for (key, val) in json_struct.items()}
    else:
        return json_struct


def _jsonify(json_struct):
    if isinstance(json_struct, list):
        return list(map(_jsonify, json_struct))
    elif isinstance(json_struct, dict):
        return {str(key): _jsonify(val) for (key, val) in json_struct.items()}
    else:
        return json_struct


def _maybe_convert_str(x):
    if x.isdigit():
        try:
            return int(x)
        except ValueError:
            pass
    try:
        return float(x)
    except ValueError:
        return x

