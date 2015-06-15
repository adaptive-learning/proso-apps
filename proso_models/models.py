from django.contrib.auth.models import User
from django.db import models
from django.db.models import F
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from proso.models.environment import CommonEnvironment, InMemoryEnvironment
from datetime import datetime
from contextlib import closing
from django.db import connection
from django.conf import settings
from proso_ab.models import Value as ABValue, Experiment as ABExperiment
from proso_user.models import Session
import re
import os.path
from decorator import cache_environment_for_item
from collections import defaultdict
from proso.django.config import instantiate_from_config, instantiate_from_json, get_global_config, get_config
from proso_common.models import Config
import json
from django.core.cache import cache
from proso.django.cache import get_request_cache, is_cache_prepared
from django.db import transaction
from proso.django.util import disable_for_loaddata, is_on_postgresql
import hashlib


ENVIRONMENT_INFO_CACHE_EXPIRATION = 30 * 60
ENVIRONMENT_INFO_CACHE_KEY = 'proso_models_env_info'


# This is hack to emulate TRUE value on both psql and sqlite
DATABASE_TRUE = '1 = 1'


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
        default_class='proso_models.models.DatabaseEnvironment',
        pass_parameters=[get_active_environment_info()['id']]
    )


def get_predictive_model():
    # predictive model is configured by active environment info
    return instantiate_from_json(get_active_environment_info()['config'])


def get_item_selector():
    return instantiate_from_config(
        'proso_models', 'item_selector',
        default_class='proso.models.item_selection.ScoreItemSelection',
        pass_parameters=[get_predictive_model()]
    )


def get_option_selector(item_selector):
    return instantiate_from_config(
        'proso_models', 'option_selector',
        default_class='proso.models.option_selection.ConfusingOptionSelection',
        pass_parameters=[item_selector]
    )


################################################################################
# Environment
################################################################################

class InMemoryDatabaseFlushEnvironment(InMemoryEnvironment):

    DROP_KEYS = [
        InMemoryEnvironment.NUMBER_OF_ANSWERS,
        InMemoryEnvironment.NUMBER_OF_FIRST_ANSWERS,
        InMemoryEnvironment.LAST_CORRECTNESS,
        InMemoryEnvironment.NUMBER_OF_CORRECT_ANSWERS,
        InMemoryEnvironment.CONFUSING_FACTOR
    ]

    def __init__(self, info):
        # key -> user -> item_primary -> item_secondary -> [(time, value)]
        InMemoryEnvironment.__init__(self)
        self._prefetched = {}
        self._info_id = info.id
        self._to_delete = []

    def prefetch(self, users, items):
        if len(users) == 0 and len(items) == 0:
            return
        users = map(str, users)
        items = map(str, items)
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT key, user_id, item_primary_id, item_secondary_id, updated, value, id
                FROM proso_models_variable
                WHERE
                    (info_id = %s OR permanent)
                AND
                    (user_id IN (''' + ','.join(users) + ''') OR user_id is NULL)
                AND
                    (
                        item_primary_id IS NULL
                        OR
                        item_primary_id IN (''' + ','.join(items) + ''')
                        OR
                        item_secondary_id IN (''' + ','.join(items) + ''')
                    )
                ''', [self._info_id])
            for row in cursor:
                self._prefetched[row[0], row[1], row[2], row[3]] = (row[4].replace(tzinfo=None), row[5], row[6])

    def read(self, key, user=None, item=None, item_secondary=None, default=None, symmetric=True):
        prefetched = self._get_prefetched(key, user, item, item_secondary, symmetric)
        if prefetched:
            return prefetched[1]
        else:
            return InMemoryEnvironment.read(
                self, key, user=user, item=item, item_secondary=item_secondary,
                default=default, symmetric=symmetric
            )

    def write(self, key, value, user=None, item=None, item_secondary=None, time=None, audit=True, symmetric=True, permanent=False):
        prefetched_key = self._prefetched_key(key, user, item, item_secondary, symmetric)
        prefetched = self._prefetched.get(prefetched_key)
        if prefetched is not None:
            self._to_delete.append(prefetched[2])
            del self._prefetched[prefetched_key]
        InMemoryEnvironment.write(
            self, key, value, user=user, item=item,
            item_secondary=item_secondary, symmetric=symmetric
        )

    def time(self, key, user=None, item=None, item_secondary=None, symmetric=True):
        prefetched = self._get_prefetched(key, user, item, item_secondary, symmetric)
        if prefetched:
            return prefetched[0]
        else:
            return InMemoryEnvironment.time(
                self, key, user=user, item=item,
                item_secondary=item_secondary, symmetric=symmetric
            )

    def flush(self, clean):
        filename_audit = os.path.join(settings.DATA_DIR, 'environment_flush_audit.csv')
        filename_variable = os.path.join(settings.DATA_DIR, 'environment_flush_variable.csv')
        with open(filename_audit, 'w') as file_audit:
            for (key, u, i_p, i_s, t, v) in self.export_audit():
                if key in self.DROP_KEYS:
                    continue
                file_audit.write(
                    '%s,%s,%s,%s,%s,%s,%s\n' % (key, u, i_p, i_s, t.strftime('%Y-%m-%d %H:%M:%S'), v, self._info_id))
        with open(filename_variable, 'w') as file_variable:
            for (key, u, i_p, i_s, p, t, v) in self.export_values():
                file_variable.write(
                    '%s,%s,%s,%s,%s,%s,%s,%s,%s\n' % (key, u, i_p, i_s, v, 0, t, p, self._info_id))
        with transaction.atomic():
            with closing(connection.cursor()) as cursor:
                cursor.execute('SET CONSTRAINTS ALL DEFERRED')
                if self._to_delete:
                    cursor.execute('DELETE FROM proso_models_variable WHERE id IN (' + ','.join(map(str, self._to_delete)) + ')')
                if clean:
                    cursor.execute('DELETE FROM proso_models_variable WHERE key IN (' + ','.join(['%s' for k in self.DROP_KEYS]) + ') AND info_id = %s', self.DROP_KEYS + [self._info_id])
                with open(filename_audit, 'r') as file_audit:
                    cursor.copy_from(
                        file_audit,
                        'proso_models_audit',
                        sep=',',
                        null='None',
                        columns=['key', 'user_id', 'item_primary_id', 'item_secondary_id', 'time', 'value', 'info_id']
                    )
                with open(filename_variable, 'r') as file_variable:
                    cursor.copy_from(
                        file_variable,
                        'proso_models_variable',
                        sep=',',
                        null='None',
                        columns=['key', 'user_id', 'item_primary_id', 'item_secondary_id', 'value', 'audit', 'updated', 'permanent', 'info_id']
                    )

    def _get_prefetched(self, key, user, item, item_secondary, symmetric):
        return self._prefetched.get(self._prefetched_key(key, user, item, item_secondary, symmetric))

    def _prefetched_key(self, key, user, item, item_secondary, symmetric):
        items = [item_secondary, item]
        if symmetric:
            items.sort()
        return (key, user, items[1], items[0])


class DatabaseEnvironment(CommonEnvironment):

    def __init__(self, info_id=None):
        self._time = None
        self._info_id = info_id

    def process_answer(self, user, item, asked, answered, time, response_time, guess, **kwargs):
        answer = Answer(
            user_id=user,
            item_id=item,
            item_asked_id=asked,
            item_answered_id=answered,
            time=time,
            response_time=response_time,
            guess=guess)
        answer.save()

    def audit(self, key, user=None, item=None, item_secondary=None, limit=100000, symmetric=True):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where_single(key, user, item, item_secondary, symmetric)
            cursor.execute(
                'SELECT time, value FROM proso_models_audit WHERE '
                + where +
                ' ORDER BY time DESC LIMIT %s',
                where_params + [limit])
            result = cursor.fetchall()
            map(lambda (d, v): (self._ensure_is_datetime(d), v), result)
            return result

    def get_items_with_values(self, key, item, user=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where_single(
                key, user, item, None, force_null=False, symmetric=False, time_shift=False)
            cursor.execute(
                '''
                SELECT
                    item_secondary_id,
                    value
                FROM
                    proso_models_variable
                WHERE
                ''' + where, where_params)
            return cursor.fetchall()

    @cache_environment_for_item()
    def get_items_with_values_more_items(self, key, items, user=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where_more_items(
                key, items, user, None, force_null=['user_id'], symmetric=False, time_shift=False)
            cursor.execute(
                '''
                SELECT
                    item_primary_id,
                    item_secondary_id,
                    value
                FROM
                    proso_models_variable
                WHERE
                ''' + where, where_params)
            result = defaultdict(list)
            for p_id, s_id, val in cursor:
                result[p_id].append((s_id, val))
            return map(lambda i: result[i], items)

    def read(self, key, user=None, item=None, item_secondary=None, default=None, symmetric=True):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where_single(key, user, item, item_secondary, symmetric=symmetric)
            if self._time is None:
                cursor.execute(
                    'SELECT value FROM proso_models_variable WHERE ' + where,
                    where_params)
                fetched = cursor.fetchone()
                return default if fetched is None else fetched[0]
            else:
                audit = self.audit(key, user, item, item_secondary, limit=1)
                if len(audit) == 0:
                    return default
                else:
                    return audit[0][1]

    @cache_environment_for_item()
    def read_more_items(self, key, items, user=None, item=None, default=None, symmetric=True):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where_more_items(key, items, user, item, symmetric=symmetric)
            if self._time is None:
                cursor.execute(
                    'SELECT item_primary_id, item_secondary_id, value FROM proso_models_variable WHERE '
                    + where,
                    where_params)
                result = cursor.fetchall()
            else:
                cursor.execute(
                    '''SELECT DISTINCT ON
                        (key, item_primary_id, item_secondary_id, user_id)
                        item_primary_id, item_secondary_id, value FROM proso_models_audit WHERE
                    ''' + where +
                    ' ORDER BY key, item_primary_id, item_secondary_id, user_id, time',
                    where_params)
                result = cursor.fetchall()
            if item is None:
                result = map(lambda (x, y, z): (x, z), result)
            else:
                result = map(lambda (x, y, z): (x, z) if y == item else (y, z), result)
            result = dict(result)
            return map(lambda key: result.get(key, default), items)

    def time(self, key, user=None, item=None, item_secondary=None, symmetric=True):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where_single(key, user, item, item_secondary, symmetric=symmetric)
            if self._time is None:
                cursor.execute(
                    'SELECT updated FROM proso_models_variable WHERE ' + where,
                    where_params)
                fetched = cursor.fetchone()
                return None if fetched is None else self._ensure_is_datetime(fetched[0])
            else:
                audit = self.audit(key, user, item, item_secondary, limit=1)
                if len(audit) == 0:
                    return None
                else:
                    return self._ensure_is_datetime(audit[0][0])

    def time_more_items(self, key, items, user=None, item=None, symmetric=True):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where_more_items(key, items, user, item, symmetric=symmetric)
            if self._time is None:
                cursor.execute(
                    'SELECT item_primary_id, item_secondary_id, updated FROM proso_models_variable WHERE '
                    + where,
                    where_params)
                result = cursor.fetchall()
            else:
                cursor.execute(
                    '''SELECT DISTINCT ON
                        (key, item_primary_id, item_secondary_id, user_id)
                        item_primary_id, item_secondary_id, time FROM proso_models_audit WHERE
                    ''' + where +
                    ' ORDER BY key, item_primary_id, item_secondary_id, user_id, time',
                    where_params)
                result = cursor.fetchall()
            if item is None:
                result = map(lambda (x, y, z): (x, z), result)
            else:
                result = map(lambda (x, y, z): (x, z) if y == item else (y, z), result)
            result = dict(result)
            return map(lambda key: result.get(key), items)

    def write(self, key, value, user=None, item=None, item_secondary=None, time=None, audit=True, symmetric=True, permanent=False):
        if permanent:
            audit = False
        if key is None:
            raise Exception('Key has to be specified')
        if value is None:
            raise Exception('Value has to be specified')
        items = [item_secondary, item]
        if symmetric:
            items = sorted(items)
        data = {
            'user_id': user,
            'item_primary_id': items[1],
            'item_secondary_id': items[0],
            'key': key,
            'info_id': self._info_id,
        }
        try:
            variable = Variable.objects.get(**data)
            if variable.permanent != permanent:
                raise Exception("Variable %s changed permanency." % key)
        except Variable.DoesNotExist:
            variable = Variable(**data)
        if variable.value != value:
            variable.value = value
            variable.audit = audit
            variable.permanent = permanent
            if not permanent:
                variable.info_id = self._info_id
            variable.updated = datetime.now() if time is None else time
            variable.save()

    def delete(self, key, user=None, item=None, item_secondary=None, symmetric=True):
        if key is None:
            raise Exception('Key has to be specified')
        items = [item_secondary, item]
        if symmetric:
            items = sorted(items)
        data = {
            'user_id': user,
            'item_primary_id': items[1],
            'item_secondary_id': items[0],
            'key': key
        }
        try:
            variable = Variable.objects.get(**data)
            if not variable.permanent:
                raise Exception("Can't delete variable %s which is not permanent." % key)
            variable.delete()
        except Variable.DoesNotExist:
            pass

    def number_of_answers(self, user=None, item=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': item}, False, for_answers=True)
            cursor.execute(
                'SELECT COUNT(id) FROM proso_models_answer WHERE '
                + where, where_params)
            return cursor.fetchone()[0]

    def number_of_correct_answers(self, user=None, item=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': item}, False, for_answers=True)
            cursor.execute(
                'SELECT COUNT(id) FROM proso_models_answer WHERE item_asked_id = item_answered_id AND '
                + where, where_params)
            return cursor.fetchone()[0]

    def number_of_first_answers(self, user=None, item=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': item}, False, for_answers=True)
            cursor.execute(
                'SELECT COUNT(1) FROM (SELECT 1 FROM proso_models_answer WHERE '
                + where + ' GROUP BY user_id, item_id) AS t', where_params)
            return cursor.fetchone()[0]

    def last_answer_time(self, user=None, item=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': item}, False, for_answers=True)
            cursor.execute(
                'SELECT MAX(time) FROM proso_models_answer WHERE '
                + where, where_params)
            return self._ensure_is_datetime(cursor.fetchone()[0])

    @cache_environment_for_item(default=0)
    def number_of_answers_more_items(self, items, user=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': items}, False, for_answers=True)
            cursor.execute(
                'SELECT item_id, COUNT(id) FROM proso_models_answer WHERE '
                + where + ' GROUP BY item_id' + ('' if user is None else ', user_id'),
                where_params)
            fetched = dict(cursor.fetchall())
            return map(lambda i: fetched.get(i, 0), items)

    @cache_environment_for_item(default=0)
    def number_of_correct_answers_more_items(self, items, user=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': items}, False, for_answers=True)
            cursor.execute(
                'SELECT item_id, COUNT(id) FROM proso_models_answer WHERE item_asked_id = item_answered_id AND '
                + where + ' GROUP BY item_id' + ('' if user is None else ', user_id'),
                where_params)
            fetched = dict(cursor.fetchall())
            return map(lambda i: fetched.get(i, 0), items)

    @cache_environment_for_item(default=0)
    def number_of_first_answers_more_items(self, items, user=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': items}, False, for_answers=True)
            cursor.execute(
                'SELECT item_id, COUNT(1) FROM (SELECT user_id, item_id FROM proso_models_answer WHERE '
                + where + ' GROUP BY user_id, item_id) AS t GROUP BY item_id' + ('' if user is None else ', user_id'),
                where_params)
            fetched = dict(cursor.fetchall())
            return map(lambda i: fetched.get(i, 0), items)
        return 0

    @cache_environment_for_item()
    def last_answer_time_more_items(self, items, user=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': items}, False, for_answers=True)
            cursor.execute(
                'SELECT item_id, MAX(time) FROM proso_models_answer WHERE '
                + where + ' GROUP BY item_id' + ('' if user is None else ', user_id'),
                where_params)
            fetched = dict(map(lambda (x, d): (x, self._ensure_is_datetime(d)), cursor.fetchall()))

            return map(lambda i: fetched.get(i, None), items)

    def shift_time(self, new_time):
        self._time = new_time

    def rolling_success(self, user, window_size=10):
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT item_asked_id = item_answered_id
                FROM proso_models_answer
                WHERE user_id = %s
                ORDER BY id DESC
                LIMIT %s
                ''', [user, window_size])
            fetched = map(lambda x: True if x[0] else False, cursor.fetchall())
            if len(fetched) < window_size:
                return None
            else:
                return sum(fetched) / float(len(fetched))

    def confusing_factor(self, item, item_secondary, user=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({
                'item_asked_id': item,
                'item_answered_id': item_secondary,
                'user_id': user
            }, force_null=False, for_answers=True)
            cursor.execute(
                '''
                SELECT
                    COUNT(proso_models_answer.id) AS confusing_factor
                FROM
                    proso_models_answer
                WHERE guess=0 AND
                ''' + where, where_params)
            return cursor.fetchone()[0]

    def confusing_factor_more_items(self, item, items, user=None):
        cache_hash = hashlib.sha1('{}_{}_{}'.format(item, sorted(items), user)).hexdigest()
        cache_key = 'confusing_factor_{}'.format(cache_hash)
        cached_json = cache.get(cache_key)
        if cached_json is None:
            with closing(connection.cursor()) as cursor:
                where, where_params = self._where({
                    'item_asked_id': item,
                    'item_answered_id': items,
                    'user_id': user
                }, force_null=False, for_answers=True)
                cursor.execute(
                    '''
                    SELECT
                        item_answered_id,
                        COUNT(id) AS confusing_factor
                    FROM
                        proso_models_answer
                    WHERE guess=0 AND
                    ''' + where + ' GROUP BY item_answered_id', where_params)
                wrongs = dict(cursor.fetchall())
                result = map(lambda i: wrongs.get(i, 0), items)
                cache.set(
                    cache_key,
                    json.dumps(result),
                    get_config('proso_models', 'confusing_factor.cache_expiration', default=24 * 60 * 60)
                )
                return result
        else:
            return json.loads(cached_json)

    def export_values():
        pass

    def export_audit():
        pass

    def _where_single(self, key, user=None, item=None, item_secondary=None, force_null=True, symmetric=True, time_shift=True, for_answers=False):
        if key is None:
            raise Exception('Key has to be specified')
        items = [item_secondary, item]
        if symmetric:
            items = sorted(items)
        return self._where({
            'user_id': user,
            'item_primary_id': items[1],
            'item_secondary_id': items[0],
            'key': key}, force_null=force_null, time_shift=time_shift, for_answers=for_answers)

    def _where_more_items(self, key, items, user=None, item=None, force_null=True, symmetric=True, time_shift=True, for_answers=False):
        if key is None:
            raise Exception('Key has to be specified')
        cond_secondary = {
            'key': key,
            'user_id': user,
            'item_primary_id': items,
            'item_secondary_id': item
        }
        if item is None or all(map(lambda x: item <= x, items)) or not symmetric:
            return self._where(cond_secondary, force_null=force_null, time_shift=time_shift, for_answers=for_answers)
        cond_primary = {
            'key': key,
            'user_id': user,
            'item_primary_id': item,
            'item_secondary_id': items
        }
        if all(map(lambda x: item >= x, items)):
            return self._where(cond_primary, force_null=force_null, time_shift=time_shift, for_answers=for_answers)
        return self._where({
            'item is primary': cond_primary,
            'item is secondary': cond_secondary
        }, force_null=force_null, time_shift=time_shift, for_answers=for_answers)

    def _where(self, condition, force_null=True, top_most=True, time_shift=True, for_answers=False):
        if isinstance(condition, tuple):
            result_cond, result_params = self._column_comparison(
                condition[0], condition[1], force_null=force_null)
        elif isinstance(condition, dict):
            conds, params = zip(*map(
                lambda x: self._where(x, force_null, top_most=False, for_answers=for_answers), condition.items()))
            params = [p for ps in params for p in ps]
            operator = ' AND '
            if any(map(lambda x: isinstance(x, dict), condition)):
                operator = ' OR '
            result_cond, result_params = operator.join(conds), params
        else:
            raise Exception("Unsupported type of condition:" + str(type(condition)))
        if top_most and not for_answers:
            result_cond = ('(%s) AND (info_id = ? OR info_id IS NULL)' % result_cond)
            result_params = result_params + [self._info_id]
        if top_most and self._time is not None and time_shift:
            result_cond = ('(%s) AND time < ?' % result_cond)
            result_params = result_params + [self._time.strftime('%Y-%m-%d %H:%M:%S')]
        result_cond = result_cond.replace('?', '%s')
        return result_cond, result_params

    def _column_comparison(self, column, value, force_null=True):
        if isinstance(value, list):
            value = list(set(value))
            contains_null = any(map(lambda x: x is None, value))
            if contains_null:
                value = filter(lambda x: x is not None, value)
            null_contains_return = (column + ' IS NULL OR ') if contains_null else ''
            if len(value) > 0:
                sorted_values = sorted(value)
                if is_on_postgresql():
                    return '({} {} = ANY(VALUES {}))'.format(
                        null_contains_return,
                        column,
                        ','.join(['(%s)' for i in value])
                    ), sorted_values
                else:
                    return '({} {} IN ({}))'.format(
                        null_contains_return,
                        column,
                        ','.join(['%s' for i in value])
                    ), sorted_values
            else:
                return '(' + null_contains_return + DATABASE_TRUE + ')', []
        elif value is not None:
            return column + ' = %s', [value]
        elif (isinstance(force_null, bool) and force_null) or (isinstance(force_null, list) and column in force_null):
            return column + ' IS NULL', []
        else:
            return DATABASE_TRUE, []

    def _ensure_is_datetime(self, value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.replace(tzinfo=None)
        else:
            matched = re.match(r'([\d -\:]*)\.\d+', value)
            if matched is not None:
                value = matched.groups()[0]
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')


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


class Item(models.Model):
    pass

    def to_json(self, nested=False):
        return {
            'object_type': 'item',
            'item_id': self.id,
            'id': self.id
        }

    class Meta:
        app_label = 'proso_models'


class AnswerManager(models.Manager):

    def count(self, user):
        return self.filter(user=user).count()

    def correct_count(self, user):
        return self.filter(user=user, item_asked=F("item_answered")).count()


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
    ab_values = models.ManyToManyField(ABValue)
    ab_values_initialized = models.BooleanField(default=False)
    guess = models.FloatField(default=0)
    config = models.ForeignKey(Config, null=True, blank=True, default=None)

    objects = AnswerManager()

    class Meta:
        app_label = 'proso_models'

    def to_json(self):
        return {
            'id': self.pk,
            'object_type': 'answer',
            'question_item_id': self.item_id,
            'item_asked_id': self.item_asked_id,
            'item_answered_id': self.item_answered_id,
            'user_id': self.user_id,
            'time': self.time.strftime('%Y-%m-%d %H:%M:%S'),
            'response_time': self.response_time,
        }


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

    class Meta:
        app_label = 'proso_models'
        index_together = [
            ['info', 'key'],
            ['info', 'key', 'user'],
            ['info', 'key', 'item_primary'],
            ['info', 'key', 'user', 'item_primary'],
            ['info', 'key', 'user', 'item_primary', 'item_secondary']
        ]


################################################################################
# Signals
################################################################################

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
    if not issubclass(sender, Answer):
        return
    environment = get_environment()
    predictive_model = get_predictive_model()
    predictive_model.predict_and_update(
        environment,
        instance.user_id,
        instance.item_id,
        instance.item_asked_id == instance.item_answered_id,
        instance.time,
        item_answered=instance.item_answered_id,
        item_asked=instance.item_asked_id)


@receiver(post_save)
@disable_for_loaddata
def insert_ab_values(sender, instance, **kwargs):
    if not issubclass(sender, Answer):
        return
    if not instance.ab_values_initialized:
        instance.ab_values_initialized = True
        for value in ABExperiment.objects.get_values(force=False):
            instance.ab_values.add(value)
        instance.save()


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
            info_id=instance.info_id)
        audit.save()


PROSO_MODELS_TO_EXPORT = [Answer]
