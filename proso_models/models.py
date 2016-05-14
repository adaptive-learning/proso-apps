from collections import defaultdict
from contextlib import closing
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.db import models
from django.db import transaction
from django.db.models import Count, F
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from proso.django.cache import get_request_cache, is_cache_prepared, get_from_request_permenent_cache, set_to_request_permanent_cache
from functools import reduce
from proso.django.config import instantiate_from_config, instantiate_from_json, get_global_config, get_config
from proso.django.models import ModelDiffMixin
from proso.django.request import load_query_json
from proso.django.util import disable_for_loaddata, cache_pure
from proso.func import fixed_point
from proso.list import flatten
from proso.metric import binomial_confidence_mean, confidence_value_to_json
from proso.models.item_selection import TestWrapperItemSelection
from proso_common.models import Config
from proso_common.models import IntegrityCheck
from proso_user.models import Session
import django.apps
import hashlib
import importlib
import json
import logging
import proso.list
import re


ENVIRONMENT_INFO_CACHE_EXPIRATION = 30 * 60
ENVIRONMENT_INFO_CACHE_KEY = 'proso_models_env_info'
ITEM_SELECTOR_CACHE_KEY = 'proso_models_item_selector'
LOGGER = logging.getLogger('django.request')


################################################################################
# getters
################################################################################

def get_active_environment_info():
    if is_cache_prepared():
        cached = get_request_cache().get(ENVIRONMENT_INFO_CACHE_KEY)
        if cached is not None:
            return cached
    cached = cache.get(ENVIRONMENT_INFO_CACHE_KEY)
    if cached is None:
        try:
            active_envinfo = EnvironmentInfo.objects.select_related('config').get(status=EnvironmentInfo.STATUS_ACTIVE)
        except EnvironmentInfo.DoesNotExist:
            config = Config.objects.from_content(get_config('proso_models', 'predictive_model', default={}))
            active_envinfo, _ = EnvironmentInfo.objects.get_or_create(config=config, status=EnvironmentInfo.STATUS_ACTIVE, revision=0)
        cached = active_envinfo.to_json()
        if is_cache_prepared():
            get_request_cache().set(ENVIRONMENT_INFO_CACHE_KEY, cached)
        if EnvironmentInfo.objects.filter(status=EnvironmentInfo.STATUS_LOADING).count() == 0:
            cache.set(ENVIRONMENT_INFO_CACHE_KEY, cached, ENVIRONMENT_INFO_CACHE_EXPIRATION)
    return cached


def get_environment():
    return instantiate_from_config(
        'proso_models', 'environment',
        default_class='proso_models.environment.DatabaseEnvironment',
        pass_parameters=[get_active_environment_info()['id']]
    )


def get_predictive_model():
    # predictive model is configured by active environment info
    return instantiate_from_json(get_active_environment_info()['config'])


def get_item_selector():
    cached = get_from_request_permenent_cache(ITEM_SELECTOR_CACHE_KEY)
    if cached is None:
        item_selector = instantiate_from_config(
            'proso_models', 'item_selector',
            default_class='proso.models.item_selection.ScoreItemSelection',
            pass_parameters=[get_predictive_model()]
        )
        nth = get_config('proso_models', 'random_test.nth')
        if nth is not None and nth > 0:
            item_selector = TestWrapperItemSelection(item_selector, nth)
        cached = item_selector
        set_to_request_permanent_cache(ITEM_SELECTOR_CACHE_KEY, cached)
    return cached


def get_options_number():
    return instantiate_from_config(
        'proso_models', 'options_count',
        default_class='proso.models.option_selection.AdjustedOptionsNumber'
    )


def get_mastery_trashold():
    return get_config("proso_models", "mastery_threshold", default=0.9)


def get_filter(request):
    return load_query_json(request.GET, "filter", "[]")


def get_option_selector(item_selector, options_number=None):
    if options_number is None:
        options_number = get_options_number()
    return instantiate_from_config(
        'proso_models', 'option_selector',
        default_class='proso.models.option_selection.CompetitiveOptionSelection',
        pass_parameters=[item_selector, options_number]
    )


def learning_curve(length, context=None, users=None, user_length=None, number_of_users=1000):
    if user_length is None:
        user_length = length
    with closing(connection.cursor()) as cursor:
        cursor.execute("SELECT id FROM proso_models_answermeta WHERE content LIKE '%%random_without_options%%'")
        meta_ids = [str(x[0]) for x in cursor.fetchall()]
    EMPTY_LEARNING_CURVE = {
        'number_of_users': 0,
        'number_of_data_points': 0,
        'success': [],
        'object_type': 'learning_curve',
    }
    if len(meta_ids) == 0:
        return EMPTY_LEARNING_CURVE

    def _get_where(context, users, meta_ids):
        _where = ['metainfo_id IN ({})'.format(','.join(meta_ids))]
        _where_params = []
        if context is not None:
            _where.append('context_id = %s')
            _where_params.append(context)
        if users is not None:
            _where.append('user_id IN ({})'.format(','.join(['%s' for _ in users])))
            _where_params += users
        return _where, _where_params

    with closing(connection.cursor()) as cursor:
        where, where_params = _get_where(context, users, meta_ids)
        cursor.execute(
            '''
            SELECT
                user_id
            FROM proso_models_answer
            WHERE ''' + ' AND '.join(where) + '''
            GROUP BY context_id, user_id
            HAVING COUNT(id) >= %s
            ORDER BY RANDOM()
            LIMIT %s
            ''', where_params + [user_length, number_of_users])
        valid_users = list(set([x[0] for x in cursor.fetchall()]))
    if len(valid_users) == 0:
        return EMPTY_LEARNING_CURVE
    with closing(connection.cursor()) as cursor:
        where, where_params = _get_where(context, valid_users, meta_ids)
        cursor.execute(
            '''
            SELECT
                context_id,
                user_id,
                item_asked_id = COALESCE(item_answered_id, -1)
            FROM proso_models_answer
            WHERE ''' + ' AND '.join(where) + '''
            ORDER BY id
            ''', where_params)
        context_answers = defaultdict(lambda: defaultdict(list))
        for row in cursor:
            context_answers[row[0]][row[1]].append(row[2])
        user_answers = [
            answers[:min(len(answers), length)] + [None for _ in range(length - min(len(answers), length))]
            for user_answers in context_answers.values()
            for answers in user_answers.values()
            if len(answers) >= user_length
        ]

        def _mean_with_confidence(xs):
            return confidence_value_to_json(binomial_confidence_mean([x for x in xs if x is not None]))

        return {
            'number_of_users': len(valid_users),
            'number_of_datapoints': len(user_answers),
            'success': list(map(_mean_with_confidence, list(zip(*user_answers)))),
            'object_type': 'learning_curve',
        }


def recommend_users(register_time_interval, number_of_answers_interval, success_rate_interval, variable_name, variable_interval, limit):
    where = []
    having = []
    params = []

    def _create_condition(column_name, interval, where, params):
        if interval[0] is not None:
            where.append('{} >= %s'.format(column_name))
            params.append(interval[0])
        if interval[1] is not None:
            where.append('{} <= %s'.format(column_name))
            params.append(interval[1])
    _create_condition('date_joined', register_time_interval, where, params)
    if variable_name is not None:
        _create_condition('proso_models_variable.value', variable_interval, where, params)
    _create_condition('AVG(CASE WHEN item_asked_id = item_answered_id THEN 1 ELSE 0 END)', success_rate_interval, having, params)
    _create_condition('COUNT(proso_models_answer.id)', number_of_answers_interval, having, params)
    having_final = ''
    where_final = ''
    if len(where) > 0:
        where_final = 'WHERE {}'.format(' AND '.join(where))
    if len(having) > 0:
        having_final = 'HAVING {}'.format(' AND '.join(having))
    if variable_name is not None:
        variable_join = '''
            INNER JOIN proso_models_variable
                ON proso_models_answer.user_id = proso_models_variable.user_id
                AND proso_models_variable.key = '{}'
                AND proso_models_variable.item_primary_id IS NULL
            '''.format(variable_name)
    else:
        variable_join = ''
    with closing(connection.cursor()) as cursor:
        cursor.execute(
            '''
            SELECT
                auth_user.id
            FROM auth_user
            INNER JOIN proso_models_answer ON auth_user.id = proso_models_answer.user_id
            ''' + variable_join + '''
            ''' + where_final + '''
            GROUP BY auth_user.id
            ''' + having_final + '''
            ORDER BY RANDOM()
            LIMIT %s
            ''', params + [limit]
        )
        return [x[0] for x in cursor.fetchall()]


################################################################################
# Integrity checks
################################################################################

class LonelyItems(IntegrityCheck):

    def check(self):
        referenced = set()
        for django_field in Item.objects.get_reference_fields(exclude_models=[Audit, Variable]):
            db_column = django_field.get_attname_column()[1]
            db_table = django_field.model._meta.db_table
            with closing(connection.cursor()) as cursor:
                cursor.execute('SELECT DISTINCT(%s) FROM %s' % (db_column, db_table))
                for (item_id,) in cursor:
                    if item_id is not None:
                        referenced.add(item_id)
        with closing(connection.cursor()) as cursor:
            cursor.execute('SELECT id from proso_models_item WHERE id NOT IN (%s)' % ','.join(map(str, referenced)))
            lonely_items = cursor.fetchall()
            if len(lonely_items) == 0:
                return None
            else:
                return {
                    'message': 'There are some not referenced items.',
                    'items': lonely_items,
                }


################################################################################
# Models
################################################################################

class EnvironmentInfo(models.Model):

    STATUS_DISABLED = 0
    STATUS_LOADING = 1
    STATUS_ENABLED = 2
    STATUS_ACTIVE = 3

    STATUS = (
        (STATUS_DISABLED, 'disabled'),
        (STATUS_LOADING, 'loading'),
        (STATUS_ENABLED, 'enabled'),
        (STATUS_ACTIVE, 'active'),
    )

    status = models.IntegerField(choices=STATUS, default=1)
    revision = models.IntegerField()
    config = models.ForeignKey(Config)
    load_progress = models.IntegerField(default=0)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('config', 'revision')

    def to_json(self, nested=False):
        return {
            'id': self.id,
            'object_type': 'environment_info',
            'status': dict(list(EnvironmentInfo.STATUS))[self.status],
            'revision': self.revision,
            'updated': self.updated.strftime('%Y-%m-%d %H:%M:%S'),
            'created': self.created.strftime('%Y-%m-%d %H:%M:%S'),
            'config': json.loads(self.config.content),
        }


class ItemTypeManager(models.Manager):

    def get_item_type(self, item_id):
        return self.get_all_types()[self.get_item_type_id(item_id)]

    @cache_pure
    def get_item_type_id(self, item_id):
        return Item.objects.get(id=item_id).item_type_id

    @cache_pure
    def get_all_types(self):
        return {item_type.id: item_type.to_json() for item_type in self.all()}

    def get_model(self, item_type_id):
        item_type = self.get_all_types()[item_type_id]
        matched = re.match('(.*)\.(\w+)', item_type['model'])
        module = importlib.import_module(matched.groups()[0])
        return getattr(module, matched.groups()[1])

    def find_object_types(self, with_answers=True):
        result = []
        langs = {}
        for django_model, django_field in Item.objects.get_reference_fields(exclude_models=[Answer, Audit, Variable, ItemRelation]):
            db_column = django_field.get_attname_column()[1]
            db_table = django_field.model._meta.db_table
            model = _model_class_name(django_model)
            if db_table not in langs:
                for _django_field in django_field.model._meta.fields:
                    if _django_field.get_attname_column()[1] == 'lang':
                        langs[db_table] = 'lang'
            result.append((model, db_table, db_column, langs.get(db_table)))
        return result


class ItemType(models.Model):

    model = models.CharField(max_length=100, null=False, blank=False)
    table = models.CharField(max_length=100, null=False, blank=False)
    foreign_key = models.CharField(max_length=100, null=False, blank=False)
    language = models.CharField(max_length=100, null=True, blank=True, default=None)
    valid = models.BooleanField(default=True)

    objects = ItemTypeManager()

    class Meta:
        unique_together = (
            ('table', 'foreign_key'),
            ('model', 'foreign_key'),
        )

    def to_json(self, nested=False):
        result = {
            'id': self.id,
            'object_type': 'item_type',
            'valid': self.valid,
            'table': self.table,
            'model': self.model,
            'foreign_key': self.foreign_key,
        }
        if self.language:
            result['language'] = self.language
        return result


class ItemManager(models.Manager):

    def item_id_to_json(self, item_id):
        return {
            'object_type': 'item',
            'id': item_id,
            'item_id': item_id,
        }

    def get_all_available_leaves(self):
        """
        Get all available leaves.
        """
        return sorted(Item.objects.filter(children=None).values_list('id', flat=True))

    def filter_all_reachable_leaves_many(self, identifier_filters, language):
        """
        Provides the same functionality as .. py:method:: ItemManager.filter_all_reachable_leaves(),
        but for more filters in the same time.

        Args:
            identifier_filters: list of identifier filters
            language (str): language used for further filtering (some objects
                for different languages share the same item

        Returns:
            list: list of list of item ids
        """
        for i, identifier_filter in enumerate(identifier_filters):
            if len(identifier_filter) == 1 and not isinstance(identifier_filter[0], list):
                identifier_filters[i] = [identifier_filter]
            if any([len(xs) == 1 and xs[0].startswith('-') for xs in identifier_filter]):
                raise Exception('Filter containing only one identifier with "-" prefix is not allowed.')
        item_identifiers = [
            identifier[1:] if identifier.startswith('-') else identifier
            for identifier_filter in identifier_filters
            for identifier in set(flatten(identifier_filter))
        ]
        translated = self.translate_identifiers(item_identifiers, language)
        leaves = self.get_leaves(list(translated.values()))
        result = []
        for identifier_filter in identifier_filters:
            filter_result = set()
            for inner_filter in identifier_filter:
                inner_result = None
                inner_neg_result = set()
                if len(inner_filter) == 0:
                    raise Exception('Empty nested filters are not allowed.')
                for identifier in inner_filter:
                    if identifier.startswith('-'):
                        inner_neg_result |= set(leaves[translated[identifier[1:]]])
                    elif inner_result is None:
                        inner_result = set(leaves[translated[identifier]])
                    else:
                        inner_result &= set(leaves[translated[identifier]])
                filter_result |= inner_result - inner_neg_result
            result.append(sorted(list(filter_result)))
        return result

    def filter_all_reachable_leaves(self, identifier_filter, language):
        """
        Get all leaves corresponding to the given filter:

        * the filter is a list of lists;
        * each of the inner list carries identifiers;
        * for each identifier, we find an item and all its reachable leaf items;
        * within the inner list we intersect the reachable items;
        * with the outer list we union the reachable items;
        * when an identifier starts with the prfix '-', we find its reachable
          leaf items and then complement them

        Example::

                A
               / \\
              B   C
             / \ / \\
            D   E   F

            [[A, C]] ----> [E, F]
            [[B, C]] ----> [E]
            [[B, -C]] ---> [D]

        Args::
            identifier_filter (list): list of lists of identifiers (some of them
                can start with the prefix '-')
            language (str): language used for further filtering (some objects
                for different languages share the same item

        Returns:
            list: list of item ids
        """
        return self.filter_all_reachable_leaves_many([identifier_filter], language)[0]

    @cache_pure
    def get_children_graph(self, item_ids):
        """
        Get a subgraph of items reachable from the given set of items throughr
        the 'child' relation.

        Args:
            item_ids (list): items which are taken as roots for the reachability

        Returns:
            dict: item id -> list of items (child items), root items are
            referenced by None key
        """

        def _children(item_ids):
            item_ids = [ii for iis in item_ids.values() for ii in iis]
            items = Item.objects.filter(id__in=item_ids, active=True).prefetch_related('children')
            return {item.id: sorted([_item.id for _item in item.children.all() if _item.active]) for item in items}
        return self._reachable_graph(item_ids, _children)

    def get_reachable_children(self, item_ids):
        return self._reachable_items(self.get_children_graph(item_ids))

    @cache_pure
    def get_parents_graph(self, item_ids):
        """
        Get a subgraph of items reachable from the given set of items through
        the 'parent' relation.

        Args:
            item_ids (list): items which are taken as roots for the reachability

        Returns:
            dict: item id -> list of items (parent items), root items are
            referenced by None key
        """
        def _parents(item_ids):
            item_ids = [ii for iis in item_ids.values() for ii in iis]
            items = Item.objects.filter(id__in=item_ids).prefetch_related('parents')
            return {item.id: sorted([_item.id for _item in item.parents.all()]) for item in items}
        return self._reachable_graph(item_ids, _parents)

    def get_reachable_parents(self, item_ids):
        return self._reachable_items(self.get_parents_graph(item_ids))

    def translate_identifiers(self, identifiers, language):
        """
        Translate a list of identifiers to item ids. Identifier is a string of
        the following form:

        <model_prefix>/<model_identifier>

        where <model_prefix> is any suffix of database table of the given model
        which uniquely specifies the table, and <model_identifier> is
        identifier of the object.

        Args:
            identifiers (list[str]): list of identifiers
            language (str): language used for further filtering (some objects
                for different languages share the same item

        Returns:
            dict: identifier -> item id
        """
        result = {}
        identifiers = set(identifiers)
        item_types = ItemType.objects.get_all_types()
        for item_type_id, type_identifiers in proso.list.group_by(identifiers, by=lambda identifier: self.get_item_type_id_from_identifier(identifier, item_types)).items():
            to_find = {}
            for identifier in type_identifiers:
                identifier_split = identifier.split('/')
                to_find[identifier_split[1]] = identifier
            kwargs = {'identifier__in': list(to_find.keys())}
            item_type = ItemType.objects.get_all_types()[item_type_id]
            model = ItemType.objects.get_model(item_type_id)
            if 'language' in item_type:
                kwargs[item_type['language']] = language
            for identifier, item_id in model.objects.filter(**kwargs).values_list('identifier', item_type['foreign_key']):
                result[to_find[identifier]] = item_id
        if len(result) != len(identifiers):
            raise Exception("Can't translate the following identifiers: {}".format(set(identifiers) - set(result.keys())))
        return result

    @cache_pure
    def get_item_type_id_from_identifier(self, identifier, item_types=None):
        """
        Get an ID of item type for the given identifier. Identifier is a string of
        the following form:

        <model_prefix>/<model_identifier>

        where <model_prefix> is any suffix of database table of the given model
        which uniquely specifies the table, and <model_identifier> is
        identifier of the object.

        Args:
            identifier (str): item identifier
            item_types (dict): ID -> item type JSON

        Returns:
            int: ID of the corresponding item type
        """
        if item_types is None:
            item_types = ItemType.objects.get_all_types()
        identifier_type, _ = identifier.split('/')
        item_types = [it for it in item_types.values() if it['table'].endswith(identifier_type)]
        if len(item_types) > 1:
            raise Exception('There is more than one item type for name "{}".'.format(identifier_type))
        if len(item_types) == 0:
            raise Exception('There is no item type for name "{}".'.format(identifier_type))
        return item_types[0]['id']

    def translate_item_ids(self, item_ids, language, is_nested=None):
        """
        Translate a list of item ids to JSON objects which reference them.

        Args:
            item_ids (list[int]): item ids
            language (str): language used for further filtering (some objects
                for different languages share the same item)
            is_nested (function): mapping from item ids to booleans, where the
                boolean value indicates whether the item is nested

        Returns:
            dict: item id -> JSON object
        """
        if is_nested is None:
            def is_nested_fun(x):
                return True
        elif isinstance(is_nested, bool):
            def is_nested_fun(x):
                return is_nested
        else:
            is_nested_fun = is_nested
        groupped = proso.list.group_by(item_ids, by=lambda item_id: ItemType.objects.get_item_type_id(item_id))
        result = {}
        for item_type_id, items in groupped.items():
            item_type = ItemType.objects.get_all_types()[item_type_id]
            model = ItemType.objects.get_model(item_type_id)
            kwargs = {'{}__in'.format(item_type['foreign_key']): items}
            if 'language' in item_type:
                kwargs[item_type['language']] = language
            if any([not is_nested_fun(item_id) for item_id in items]) and hasattr(model.objects, 'prepare_related'):
                objs = model.objects.prepare_related()
            else:
                objs = model.objects
            for obj in objs.filter(**kwargs):
                item_id = getattr(obj, item_type['foreign_key'])
                result[item_id] = obj.to_json(nested=is_nested_fun(item_id))
        return result

    def get_leaves(self, item_ids):
        """
        Get mapping of items to their reachable leaves. Leaves having
        inactive relations to other items are omitted.

        Args:
            item_ids (list): items which are taken as roots for the reachability

        Returns:
            dict: item id -> list of items (reachable leaves)
        """
        children = self.get_children_graph(item_ids)

        def _get_leaves(item_id):
            leaves = set()

            def __search(item_ids):
                result = set(flatten([children.get(item_id, []) for item_id in item_ids]))
                new_leaves = {item_id for item_id in result if item_id not in children.keys()}
                leaves.update(new_leaves)
                return result - new_leaves

            fixed_point(
                is_zero=lambda to_visit: len(to_visit) == 0,
                minus=lambda to_visit, visited: to_visit - visited,
                plus=lambda visited_x, visited_y: visited_x | visited_y,
                f=__search,
                x={item_id}
            )
            counts = self.get_children_counts(active=None)
            leaves = {leaf for leaf in leaves if counts[leaf] == 0}
            return leaves if len(leaves) > 0 else {item_id}

        return {item_id: _get_leaves(item_id) for item_id in item_ids}

    def get_all_leaves(self, item_ids):
        """
        Get all leaves reachable from the given set of items. Leaves having
        inactive relations to other items are omitted.

        Args:
            item_ids (list): items which are taken as roots for the reachability

        Returns:
            set: leaf items which are reachable from the given set of items
        """
        children = self.get_children_graph(item_ids)
        froms = set(children.keys())
        tos = set([ii for iis in children.values() for ii in iis])
        counts = self.get_children_counts(active=None)
        return sorted([leaf for leaf in ((set(item_ids) | tos) - froms) if counts[leaf] == 0])

    def get_reference_fields(self, exclude_models=None):
        """
        Get all Django model fields which reference the Item model.
        """
        if exclude_models is None:
            exclude_models = []
        result = []
        for django_model in django.apps.apps.get_models():
            if any([issubclass(django_model, m) for m in exclude_models]):
                continue
            for django_field in django_model._meta.fields:
                if isinstance(django_field, models.ForeignKey) and django_field.related.to == Item:
                    result = [(m, f) for (m, f) in result if not issubclass(django_model, m)]
                    result.append((django_model, django_field))
        return result

    def override_parent_subgraph(self, parent_subgraph, invisible_edges=None):
        """
        Get all items with outcoming edges from the given subgraph, drop all
        their child relations, and then add children according to the given
        subgraph.

        Args:
            children_subgraph (dict): item id -> list of chidlren (item ids)
            invisible_edges (list|set): set of (from, to) tuples specifying
                invisible edges
        """
        with transaction.atomic():
            if invisible_edges is None:
                invisible_edges = set()
            children = list(parent_subgraph.keys())
            all_old_relations = dict(proso.list.group_by(
                list(ItemRelation.objects.filter(child_id__in=children)),
                by=lambda relation: relation.child_id
            ))
            to_delete = set()
            for child_id, parents in parent_subgraph.items():
                old_relations = {
                    relation.parent_id: relation
                    for relation in all_old_relations.get(child_id, [])
                }
                for parent_id in parents:
                    if parent_id not in old_relations:
                        ItemRelation.objects.create(
                            parent_id=parent_id,
                            child_id=child_id,
                            visible=(child_id, parent_id) not in invisible_edges
                        )
                    elif old_relations[parent_id].visible != (child_id, parent_id) not in invisible_edges:
                        old_relations[parent_id].visible = (child_id, parent_id) not in invisible_edges
                        old_relations[parent_id].save()
                to_delete |= {old_relations[parent_id].pk for parent_id in set(old_relations.keys()) - set(parents)}
            ItemRelation.objects.filter(pk__in=to_delete).delete()

    def override_children_subgraph(self, children_subgraph, invisible_edges=None):
        """
        Get all items with outcoming edges from the given subgraph, drop all
        their child relations, and then add children according to the given
        subgraph.

        Args:
            children_subgraph (dict): item id -> list of chidlren (item ids)
            invisible_edges (list|set): set of (from, to) tuples specifying
                invisible edges
        """
        with transaction.atomic():
            if invisible_edges is None:
                invisible_edges = set()
            parents = list(children_subgraph.keys())
            all_old_relations = dict(proso.list.group_by(
                list(ItemRelation.objects.filter(parent_id__in=parents)),
                by=lambda relation: relation.parent_id
            ))
            to_delete = set()
            for parent_id, children in children_subgraph.items():
                old_relations = {
                    relation.child_id: relation
                    for relation in all_old_relations.get(parent_id, [])
                }
                for child_id in children:
                    if child_id not in old_relations:
                        ItemRelation.objects.create(
                            parent_id=parent_id,
                            child_id=child_id,
                            visible=(parent_id, child_id) not in invisible_edges
                        )
                    elif old_relations[child_id].visible != (parent_id, child_id) not in invisible_edges:
                        old_relations[child_id].visible = (parent_id, child_id) not in invisible_edges
                        old_relations[child_id].save()
                to_delete |= {old_relations[child_id].pk for child_id in set(old_relations.keys()) - set(children)}
            ItemRelation.objects.filter(pk__in=to_delete).delete()

    @cache_pure
    def get_children_counts(self, active=True):
        query = self
        if active is not None:
            query = query.filter(children__active=active)
        return dict(query.annotate(c=Count('children')).values_list('pk', 'c'))

    def _reachable_graph(self, item_ids, neighbors):
        return {i: deps for i, deps in fixed_point(
            is_zero=lambda xs: len(xs) == 0,
            minus=lambda xs, ys: {x: vs for (x, vs) in xs.items() if x not in ys},
            plus=lambda xs, ys: dict(list(xs.items()) + list(ys.items())),
            f=neighbors,
            x={None: item_ids}).items() if len(deps) > 0}

    def _reachable_items(self, graph):
        return {i: sorted(list(fixed_point(
            is_zero=lambda xs: len(xs) == 0,
            minus=lambda xs, ys: xs - ys,
            plus=lambda xs, ys: xs | ys,
            f=lambda xs: reduce(lambda a, b: a | b, [set(graph.get(x, [])) for x in xs], set()),
            x={i}
        ) - {i})) for i in graph[None]}


class Item(models.Model, ModelDiffMixin):

    # This field should not be NULL, but historically there is a huge number of
    # items in running systems without specified item type.
    # TODO: remove 'null=True'
    item_type = models.ForeignKey(ItemType, null=True)
    children = models.ManyToManyField(
        'self', related_name='parents',
        symmetrical=False, through='ItemRelation',
        through_fields=('parent', 'child')
    )
    active = models.BooleanField(default=True)

    objects = ItemManager()

    def to_json(self, nested=False):
        result = {
            'object_type': 'item',
            'item_id': self.id,
            'id': self.id
        }
        if not nested and self.item_type:
            result['item_type'] = self.item_type.to_json(nested=True)
        return result

    def __str__(self):
        return "Item {0.id}".format(self)

    class Meta:
        app_label = 'proso_models'


class ItemRelation(models.Model, ModelDiffMixin):

    parent = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='parent_relations')
    child = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='child_relations')
    visible = models.BooleanField(default=True)
    active = models.BooleanField(default=True)


class AnswerMetaManager(models.Manager):

    def from_content(self, content):
        if not isinstance(content, str):
            content = json.dumps(content, sort_keys=True)
        with transaction.atomic():
            try:
                content_hash = get_content_hash(content)
                return self.get(content_hash=content_hash)
            except AnswerMeta.DoesNotExist:
                answer_meta = AnswerMeta(content=content, content_hash=content_hash)
                answer_meta.save()
                return answer_meta


class AnswerMeta(models.Model):

    content = models.TextField(null=False, blank=False)
    content_hash = models.CharField(max_length=40, null=False, blank=False, db_index=True, unique=True)

    objects = AnswerMetaManager()

    def to_json(self, nested=False):
        return {
            'content': self.content,
            'content_hash': self.content_hash,
        }


class PracticeContextManager(models.Manager):

    def from_content(self, content):
        if not isinstance(content, str):
            content = json.dumps(content, sort_keys=True)
        with transaction.atomic():
            try:
                content_hash = get_content_hash(content)
                return self.get(content_hash=content_hash)
            except PracticeContext.DoesNotExist:
                practice_context = PracticeContext(content=content, content_hash=content_hash)
                practice_context.save()
                return practice_context


class PracticeContext(models.Model):

    content = models.TextField(null=False, blank=False)
    content_hash = models.CharField(max_length=40, null=False, blank=False, db_index=True, unique=True)

    objects = PracticeContextManager()

    def to_json(self, nested=False):
        return {
            'content': self.content,
            'content_hash': self.content_hash,
        }

    def __str__(self):
        return "{0.content}".format(self)


class AnswerManager(models.Manager):

    def count(self, user):
        return self.filter(user=user).count()

    def correct_count(self, user):
        return self.filter(user=user, item_asked=F("item_answered")).count()

    def from_json(self, json_object, practice_context, user_id, object_class=None):
        if object_class is None:
            object_class = Answer
        kwargs = {}
        for key in ['item_id', 'item_asked_id', 'item_answered_id', 'response_time', 'lang', 'guess']:
            if key in json_object:
                kwargs[key] = json_object[key]
        if 'time_gap' in json_object:
            kwargs.time = datetime.now() - timedelta(seconds=json_object["time_gap"])
        if 'question_type' in json_object:
            kwargs['type'] = json_object['question_type']
        kwargs['metainfo'] = None if 'meta' not in json_object else AnswerMeta.objects.from_content(json_object['meta'])
        return object_class.objects.create(
            context=practice_context, user_id=user_id, **kwargs)

    def answer_class(self, name):
        camel_case = ''.join([x.capitalize() for x in name.split('_')])
        result = []
        for subclass in Answer.__subclasses__():
            if _model_class_name(subclass).endswith(camel_case):
                result.append(subclass)
        if len(result) > 1:
            raise Exception('There is more than one answer class for name "{}".'.format(name))
        if len(result) == 0:
            raise Exception('There is no answer class for name "{}".'.format(name))
        return result[0]


class Answer(models.Model):

    user = models.ForeignKey(User)
    session = models.ForeignKey(Session, null=True, blank=True, default=None)
    item = models.ForeignKey(Item, related_name='item_answers')
    item_asked = models.ForeignKey(Item, related_name='item_asked_answers')
    item_answered = models.ForeignKey(
        Item,
        null=True,
        blank=True,
        default=None,
        related_name='item_answered_answers')
    time = models.DateTimeField(default=datetime.now)
    response_time = models.IntegerField(null=False, blank=False)
    guess = models.FloatField(default=0)
    config = models.ForeignKey(Config, null=True, blank=True, default=None)
    context = models.ForeignKey(PracticeContext, null=True, blank=True, default=None)
    metainfo = models.ForeignKey(AnswerMeta, null=True, blank=True, default=None)
    type = models.CharField(max_length=10)
    # This field should not be NULL, but historically there is a huge number of
    # answer in running systems without specified language.
    lang = models.CharField(max_length=2, null=True, blank=True, default=None)

    objects = AnswerManager()

    class Meta:
        app_label = 'proso_models'
        index_together = [
            ['user', 'context'],
        ]

    def to_json(self):
        result = {
            'id': self.pk,
            'object_type': 'answer',
            'item_id': self.item_id,
            'item_asked_id': self.item_asked_id,
            'item_answered_id': self.item_answered_id,
            'user_id': self.user_id,
            'time': self.time.strftime('%Y-%m-%d %H:%M:%S'),
            'response_time': self.response_time
        }
        if self.lang is not None:
            result['lang'] = self.lang
        if self.context is not None:
            result['context'] = self.context.to_json(nested=True)
        if self.metainfo is not None:
            result['meta'] = self.metainfo.to_json(nested=True)
        return result


class Variable(models.Model):

    user = models.ForeignKey(User, null=True, blank=True, default=None)
    item_primary = models.ForeignKey(
        Item,
        null=True,
        blank=True,
        default=None,
        related_name='item_primary_variables')
    item_secondary = models.ForeignKey(
        Item,
        null=True,
        blank=True,
        default=None,
        related_name='item_secondary_variables')
    permanent = models.BooleanField(default=False)
    key = models.CharField(max_length=50)
    value = models.FloatField()
    audit = models.BooleanField(default=True)
    updated = models.DateTimeField(default=datetime.now)
    info = models.ForeignKey(EnvironmentInfo, null=True, blank=True, default=None)
    answer = models.ForeignKey(Answer, null=True, blank=True, default=None)

    def __str__(self):
        return str({
            'user': self.user_id,
            'key': self.key,
            'item_primary': self.item_primary_id,
            'item_secondary': self.item_secondary_id,
            'value': self.value,
            'permanent': self.permanent
        })

    class Meta:
        app_label = 'proso_models'
        unique_together = ('info', 'key', 'user', 'item_primary', 'item_secondary')
        index_together = [
            ['info', 'key'],
            ['info', 'key', 'user'],
            ['info', 'key', 'item_primary'],
            ['info', 'key', 'user', 'item_primary'],
            ['info', 'key', 'user', 'item_primary', 'item_secondary']
        ]


class Audit(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, default=None)
    item_primary = models.ForeignKey(
        Item,
        null=True,
        blank=True,
        default=None,
        related_name='item_primary_audits')
    item_secondary = models.ForeignKey(
        Item,
        null=True,
        blank=True,
        default=None,
        related_name='item_secondary_audits')
    key = models.CharField(max_length=50)
    value = models.FloatField()
    time = models.DateTimeField(default=datetime.now)
    info = models.ForeignKey(EnvironmentInfo, null=True, blank=True, default=None)
    answer = models.ForeignKey(Answer, null=True, blank=True, default=None)

    class Meta:
        app_label = 'proso_models'
        index_together = [
            ['info', 'key'],
            ['info', 'key', 'user'],
            ['info', 'key', 'item_primary'],
            ['info', 'key', 'user', 'item_primary'],
            ['info', 'key', 'user', 'item_primary', 'item_secondary']
        ]


def get_content_hash(content):
    return hashlib.sha1(content.encode()).hexdigest()


def _model_class_name(django_model):
    # HACK: I haven't found other way to obtain the class, because
    # "type" function returns ModelBase from Django.
    return str(django_model).replace("<class '", "").replace("'>", "")


################################################################################
# Signals
################################################################################

def init_content_hash(instance):
    if instance.content is not None and instance.content_hash is None:
        instance.content_hash = get_content_hash(instance.content)


@receiver(pre_save, sender=AnswerMeta)
@disable_for_loaddata
def init_content_hash_answer_meta(sender, instance, **kwargs):
    init_content_hash(instance)


@receiver(pre_save)
@disable_for_loaddata
def handle_response_time_bug(sender, instance, **kwargs):
    if not issubclass(sender, Answer):
        return
    if instance.response_time is None or instance.response_time > 1000 * 60 * 60 * 24 or instance.response_time < 0:
        LOGGER.warn('There is a wrong value {} for response time, user {}, time {}, item asked {}'.format(
            instance.response_time, instance.user_id, instance.time, instance.item_asked_id))
        instance.response_time = -1


@receiver(pre_save, sender=PracticeContext)
@disable_for_loaddata
def init_content_hash_practice_context(sender, instance, **kwargs):
    init_content_hash(instance)


@receiver(pre_save)
@disable_for_loaddata
def init_session(sender, instance, **kwargs):
    if not issubclass(sender, Answer):
        return
    if instance.session_id is None:
        instance.session_id = Session.objects.get_current_session_id()


@receiver(pre_save)
@disable_for_loaddata
def init_config(sender, instance, **kwargs):
    if not issubclass(sender, Answer):
        return
    if instance.config_id is None:
        instance.config_id = Config.objects.from_content(get_global_config()).id


@receiver(post_save)
@disable_for_loaddata
def update_predictive_model(sender, instance, **kwargs):
    if not issubclass(sender, Answer) or not kwargs['created']:
        return
    environment = get_environment()
    # We want to make the prediction before the answer is saved,
    # but we need answer id to track it.
    environment.shift_answers(instance.pk)
    environment.avoid_audit(True)
    predictive_model = get_predictive_model()
    predictive_model.predict_and_update(
        environment,
        instance.user_id,
        instance.item_id,
        instance.item_asked_id == instance.item_answered_id,
        instance.time,
        instance.pk,
        item_answered=instance.item_answered_id,
        item_asked=instance.item_asked_id)


@receiver(post_save, sender=Variable)
@disable_for_loaddata
def log_audit(sender, instance, **kwargs):
    if instance.audit:
        audit = Audit(
            user_id=instance.user_id,
            item_primary=instance.item_primary,
            item_secondary=instance.item_secondary,
            key=instance.key,
            value=instance.value,
            time=instance.updated,
            info_id=instance.info_id,
            answer=instance.answer)
        audit.save()


@receiver(pre_save, sender=ItemRelation)
def relation_activity(sender, instance, **kwargs):
    instance.active = instance.child.active


@receiver(post_save, sender=Item)
def activity_of_environment_relation(sender, instance, **kwargs):
    if not kwargs['created'] and 'active' in instance.diff:
        for relation in ItemRelation.objects.filter(child_id=instance.id):
            relation.active = instance.active
            relation.save()


@receiver(post_save, sender=ItemRelation)
def init_environment_relation(sender, instance, **kwargs):
    environment = get_environment()
    if instance.visible and instance.active:
        parent = instance.parent_id
        child = instance.child_id
        environment.write("child", 1, item=parent, item_secondary=child, symmetric=False, permanent=True)
        environment.write("parent", 1, item=child, item_secondary=parent, symmetric=False, permanent=True)
    elif (not instance.visible or not instance.active) and not kwargs['created']:
        parent = instance.parent_id
        child = instance.child_id
        environment.delete("child", item=parent, item_secondary=child, symmetric=False)
        environment.delete("parent", item=child, item_secondary=parent, symmetric=False)


@receiver(post_delete, sender=ItemRelation)
def drop_environment_relation(sender, instance, **kwargs):
    environment = get_environment()
    parent = instance.parent_id
    child = instance.child_id
    environment.delete("child", item=parent, item_secondary=child, symmetric=False)
    environment.delete("parent", item=child, item_secondary=parent, symmetric=False)


PROSO_MODELS_TO_EXPORT = [Answer]
PROSO_INTEGRITY_CHECKS = [LonelyItems]
