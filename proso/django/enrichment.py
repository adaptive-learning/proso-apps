"""
This module provides enrichment for JSON objects.

    .. testsetup::

        request = None

    .. testcode::

        from pprint import pprint
        from proso.django.enrichment import register_object_type_enricher, enrich_json_objects_by_object_type


        # Firstly, we create a few enrichers.
        def global_enricher(request, json_list, nested):
            for json in json_list:
                json['globally_enriched'] = 1


        def local_enricher(request, json_list, nested):
            for json in json_list:
                json['locally_enriched'] = json.get('globally_enriched', 0) + 1

        register_object_type_enricher(['parent', 'dog', 'child'], global_enricher)
        register_object_type_enricher(['parent'], local_enricher, [global_enricher])

        # Imagine we have the following data. We can enrich them.
        data = [
            {'object_type': 'parent', 'children': [{'object_type': 'child'}, {'object_type': 'child'}]},
            {'object_type': 'parent', 'children': [{'object_type': 'child'}]},
            {'object_type': 'dog'},
        ]
        enrich_json_objects_by_object_type(request, data)

        # Now, we have enriched data.
        pprint(data)

    .. testoutput::

        [{'children': [{'globally_enriched': 1, 'object_type': 'child'},
                       {'globally_enriched': 1, 'object_type': 'child'}],
          'globally_enriched': 1,
          'locally_enriched': 2,
          'object_type': 'parent'},
         {'children': [{'globally_enriched': 1, 'object_type': 'child'}],
          'globally_enriched': 1,
          'locally_enriched': 2,
          'object_type': 'parent'},
         {'globally_enriched': 1, 'object_type': 'dog'}]
"""

from collections import defaultdict
from proso.func import is_lambda
from proso.list import flatten
from threading import Lock
from time import time
import logging


LOGGER = logging.getLogger('django.request')


_OBJECT_TYPE_ENRICHERS_LOCK = Lock()

_OBJECT_TYPE_ENRICHERS = {}
_OBJECT_TYPE_ENRICHER_ORDER = None


def enrich_json_objects_by_object_type(request, value):
    """
    Take the given value and start enrichment by object_type. The va

    Args:
        request (django.http.request.HttpRequest): request which is currently processed
        value (dict|list|django.db.models.Model):
            in case of django.db.models.Model object (or list of these
            objects), to_json method is invoked

    Returns:
        dict|list
    """
    time_start_globally = time()
    if isinstance(value, list):
        json = [x.to_json() if hasattr(x, "to_json") else x for x in value]
    else:
        if isinstance(value, dict):
            json = value
        else:
            json = value.to_json()
    objects, nested = _collect_json_objects(json, by='object_type')
    for enricher_info in _get_OBJECT_TYPE_ENRICHER_ORDER():
        if len(enricher_info['object_types']) > 0:
            enricher_objects = flatten([objects.get(object_type, []) for object_type in enricher_info['object_types']])
            enricher_nested = any([nested.get(object_type, False) for object_type in enricher_info['object_types']])
        else:
            enricher_objects = flatten(objects.values())
            enricher_nested = any(nested.values())
        if len(enricher_objects) > 0:
            time_start = time()
            enricher_info['enricher'](request, enricher_objects, enricher_nested)
            LOGGER.debug('enrichment "{}" took {} seconds'.format(enricher_info['enricher_name'], time() - time_start))
            if not enricher_info['pure']:
                # if the enricher modified object types we must collect objects
                # again
                objects, nested = _collect_json_objects(json, by='object_type')
    LOGGER.debug('The whole enrichment of json objects by their object_type took {} seconds.'.format(time() - time_start_globally))
    return json


def register_object_type_enricher(object_types, enricher, dependencies=None, priority=0, pure=True):
    if dependencies is None:
        dependencies = []
    global _OBJECT_TYPE_ENRICHERS
    enricher_name = _enricher_name(enricher)
    dependency_names = [_enricher_name(fun) for fun in dependencies]
    with _OBJECT_TYPE_ENRICHERS_LOCK:
        if enricher_name in _OBJECT_TYPE_ENRICHERS:
            _OBJECT_TYPE_ENRICHERS['dependencies'] = set(_OBJECT_TYPE_ENRICHERS['dependencies'] + dependencies)
            _OBJECT_TYPE_ENRICHERS['object_types'] = set(_OBJECT_TYPE_ENRICHERS['object_types'] + object_types)
        else:
            _OBJECT_TYPE_ENRICHERS[enricher_name] = {
                'object_types': object_types if object_types is not None else [],
                'enricher': enricher,
                'enricher_name': enricher_name,
                'dependencies': dependency_names,
                'priority': priority,
                'pure': pure,
            }
        global _OBJECT_TYPE_ENRICHER_ORDER
        _OBJECT_TYPE_ENRICHER_ORDER = None


def enrich_by_predicate(request, json, fun, predicate, skip_nested=False, **kwargs):
    """
    Take the JSON, find all its subparts satisfying the given condition and
    them by the given function. Other key-word arguments are passed to the function.

    .. testsetup::

        from pprint import pprint
        from proso.django.enrichment import enrich_by_predicate
        request = None

    .. testcode::

        def enricher(request, json_list, nested):
            for json_object in json_list:
                json_object['enriched'] = True

        enriched = enrich_by_predicate(
            request,
            [{'object_type': 'example_1'}, {'object_type': 'example_2'}],
            enricher,
            lambda x: True
        )

        pprint(enriched)

    .. testoutput::

        [{'enriched': True, 'object_type': 'example_1'},
         {'enriched': True, 'object_type': 'example_2'}]


    Args:
        request (django.http.request.HttpRequest): request which is currently processed
        json (list|dict): in-memory representation of JSON
        fun: function which is be applied on found objects
        predicate: function which is applied on all objects to determine which
            objects should be processed further
        skip_nested: ignore nested objects

    Returns:
        list|dict: transformed JSON
    """
    time_start = time()
    collected = []
    memory = {'nested': False}

    def _collect(json_inner, nested):
        if nested and skip_nested:
            return
        if isinstance(json_inner, list):
            list(map(lambda x: _collect(x, nested), json_inner))
        elif isinstance(json_inner, dict):
            if predicate(json_inner):
                collected.append(json_inner)
                if nested:
                    memory['nested'] = True
            list(map(lambda x: _collect(x, True), list(json_inner.values())))
    _collect(json, False)
    if len(collected) > 0:
        fun(request, collected, memory['nested'], **kwargs)
    LOGGER.debug("enrichment of JSON by predicate by '%s' function took %s seconds", fun.__name__, (time() - time_start))
    return json


def enrich_by_object_type(request, json, fun, object_type, skip_nested=False, **kwargs):
    """
    Take the JSON, find its subparts having the given object part and transform
    them by the given function. Other key-word arguments are passed to the function.

    .. testsetup::

        from pprint import pprint
        from proso.django.enrichment import enrich_by_object_type
        request = None

    .. testcode::

        def enricher(request, json_list, nested):
            for json_object in json_list:
                json_object['enriched'] = True

        enriched = enrich_by_object_type(
            request,
            [{'object_type': 'example_1'}, {'object_type': 'example_2'}],
            enricher,
            ['example_1']
        )

        pprint(enriched)

    .. testoutput::

        [{'enriched': True, 'object_type': 'example_1'}, {'object_type': 'example_2'}]

    Args:
        request (django.http.request.HttpRequest): request which is currently processed
        json (list|dict): in-memory representation of JSON
        fun: function which is be applied on found objects
        object_type(str|list): object type or list of object types
        skip_nested: ignore nested objects

    Returns:
        list|dict: transformed JSON
    """
    if not isinstance(object_type, list):
        object_type = [object_type]
    predicate = lambda x: 'object_type' in x and x['object_type'] in object_type
    return enrich_by_predicate(request, json, fun, predicate, skip_nested=skip_nested, **kwargs)


def _collect_json_objects(json, by='object_type'):
    by_fun = lambda x: x.get(by) if isinstance(by, str) else by
    collected = defaultdict(list)
    nested_memory = {}

    def _collect(json_inner, nested):
        if isinstance(json_inner, list):
            [_collect(x, nested) for x in json_inner]
        elif isinstance(json_inner, dict):
            json_inner_by = by_fun(json_inner)
            if json_inner_by is not None:
                collected[json_inner_by].append(json_inner)
                if nested:
                    nested_memory[json_inner_by] = True
            [_collect(x, True) for x in json_inner.values()]
    _collect(json, False)
    # HACK: The problem is we want to ignore some objects (like object_type
    # question in proso_models).
    nested_memory = {key: False for key, _ in nested_memory.items()}
    return collected, {key: nested_memory.get(key, False) for key in collected.keys()}


def _enricher_name(enricher_fun):
    if is_lambda(enricher_fun):
        raise Exception('The enricher function can not be a lambda function.')
    return '{}.{}'.format(enricher_fun.__module__, enricher_fun.__name__)


def _get_OBJECT_TYPE_ENRICHER_ORDER():
    with _OBJECT_TYPE_ENRICHERS_LOCK:
        global _OBJECT_TYPE_ENRICHER_ORDER
        if _OBJECT_TYPE_ENRICHER_ORDER is None:
            global _OBJECT_TYPE_ENRICHERS
            visited = set()
            stack = set()
            order = []
            enrichers = _OBJECT_TYPE_ENRICHERS
            refs = set(flatten([enricher_info['dependencies'] for enricher_info in enrichers.values()]))
            roots = set(enrichers.keys()) - refs

            def _visit(enricher_info):
                if enricher_info['enricher_name'] in visited:
                    return
                if enricher_info['enricher_name'] in stack:
                    raise Exception('There is a cycle in dependencies of enrichers.')
                stack.add(enricher_info['enricher_name'])
                visited.add(enricher_info['enricher_name'])
                for enricher_dep in sorted(enricher_info['dependencies'], key=lambda name: enrichers[name]['priority']):
                    _visit(enrichers[enricher_dep])
                stack.remove(enricher_info['enricher_name'])
                order.append(enricher_info)

            for enricher_name, enricher_info in sorted(enrichers.items(), key=lambda x: x[1]['priority']):
                if enricher_name not in roots:
                    continue
                _visit(enricher_info)
            indexes = dict([(enricher_info['enricher_name'], i) for (i, enricher_info) in enumerate(order)])
            _OBJECT_TYPE_ENRICHER_ORDER = sorted(order, key=lambda e: indexes[e['enricher_name']])
        return _OBJECT_TYPE_ENRICHER_ORDER
