from .decorator import cache_environment_for_item
from .models import Answer, Variable
from collections import defaultdict
from contextlib import closing
from datetime import datetime
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db import transaction
from proso.django.config import get_config
from proso.django.util import is_on_postgresql
from proso.models.environment import CommonEnvironment, InMemoryEnvironment
import logging
import os.path
import re

LOGGER = logging.getLogger('django.request')

# This is hack to emulate TRUE value on both psql and sqlite
DATABASE_TRUE = '1 = 1'


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
        users = list(map(str, users))
        items = list(map(str, items))
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

    def write(self, key, value, user=None, item=None, item_secondary=None, time=None, audit=True, symmetric=True, permanent=False, answer=None):
        prefetched_key = self._prefetched_key(key, user, item, item_secondary, symmetric)
        prefetched = self._prefetched.get(prefetched_key)
        if prefetched is not None:
            self._to_delete.append(prefetched[2])
            del self._prefetched[prefetched_key]
        InMemoryEnvironment.write(
            self, key, value, user=user, item=item,
            item_secondary=item_secondary, time=time, audit=audit,
            symmetric=symmetric, permanent=permanent, answer=answer
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
            for (key, u, i_p, i_s, t, a, v) in self.export_audit():
                if key in self.DROP_KEYS:
                    continue
                file_audit.write(
                    '%s,%s,%s,%s,%s,%s,%s,%s\n' % (key, u, i_p, i_s, t.strftime('%Y-%m-%d %H:%M:%S'), a, v, self._info_id))
        with open(filename_variable, 'w') as file_variable:
            for (key, u, i_p, i_s, p, t, a, v) in self.export_values():
                file_variable.write(
                    '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' % (key, u, i_p, i_s, v, 0, t, p, self._info_id))
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
                        columns=['key', 'user_id', 'item_primary_id', 'item_secondary_id', 'time', 'answer_id', 'value', 'info_id']
                    )
                with open(filename_variable, 'r') as file_variable:
                    cursor.copy_from(
                        file_variable,
                        'proso_models_variable',
                        sep=',',
                        null='None',
                        columns=['key', 'user_id', 'item_primary_id', 'item_secondary_id', 'value', 'audit', 'updated', 'answer_id', 'permanent', 'info_id']
                    )

    def _get_prefetched(self, key, user, item, item_secondary, symmetric):
        return self._prefetched.get(self._prefetched_key(key, user, item, item_secondary, symmetric))

    def _prefetched_key(self, key, user, item, item_secondary, symmetric):
        items = [item_secondary, item]
        if symmetric and item is not None and item_secondary is not None:
            items.sort()
        return (key, user, items[1], items[0])


class DatabaseEnvironment(CommonEnvironment):

    def __init__(self, info_id=None):
        self._time = None
        self._before_answer = None
        self._avoid_audit = False
        self._info_id = info_id

    def process_answer(self, user, item, asked, answered, time, answer_id, response_time, guess, **kwargs):
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
            list(map(lambda d_v: (self._ensure_is_datetime(d_v[0]), d_v[1]), result))
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
            return [result[i] for i in items]

    def read(self, key, user=None, item=None, item_secondary=None, default=None, symmetric=True):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where_single(key, user, item, item_secondary, symmetric=symmetric)
            if (self._time is None and self._before_answer is None) or self._avoid_audit:
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
            if (self._time is None and self._before_answer is None) or self._avoid_audit:
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
                result = [(x_y_z[0], x_y_z[2]) for x_y_z in result]
            else:
                result = [(x_y_z1[0], x_y_z1[2]) if x_y_z1[1] == item else (x_y_z1[1], x_y_z1[2]) for x_y_z1 in result]
            result = dict(result)
            return [result.get(k, default) for k in items]

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
                result = [(x_y_z2[0], x_y_z2[2]) for x_y_z2 in result]
            else:
                result = [(x_y_z3[0], x_y_z3[2]) if x_y_z3[1] == item else (x_y_z3[1], x_y_z3[2]) for x_y_z3 in result]
            result = dict(result)
            return [result.get(k) for k in items]

    def write(self, key, value, user=None, item=None, item_secondary=None, time=None, audit=True, symmetric=True, permanent=False, answer=None):
        if permanent:
            audit = False
        if key is None:
            raise Exception('Key has to be specified')
        if value is None:
            raise Exception('Value has to be specified')
        items = [item_secondary, item]
        if symmetric and item is not None and item_secondary is not None:
            items = self._sorted(items)
        data = {
            'user_id': user,
            'item_primary_id': items[1],
            'item_secondary_id': items[0],
            'key': key,
        }
        if not permanent:
            data['info_id'] = self._info_id,
        # HACK: There is a race condition creating more variables, so it is
        #       not possible to get exactly one. I hope this scenario does
        #       not happen very often.
        variables = list(Variable.objects.filter(**data))
        if len(variables) == 0:
            variable = Variable(**data)
        else:
            if len(variables) == 1:
                variable = variables[0]
            else:
                LOGGER.error('There is a duplicate variable with the following data: {}. Start cleaning.'.format(data))
                variable = max(variables, key=lambda variable: variable.id)
                for var in [var for var in variables if var.id != variable.id]:
                    var.delete()
            if variable.permanent != permanent:
                raise Exception("Variable %s changed permanency." % key)
        if variable.value == value:
            return
        variable.value = value
        variable.audit = audit
        variable.permanent = permanent
        variable.answer_id = answer
        if not permanent:
            variable.info_id = self._info_id
        variable.updated = datetime.now() if time is None else time
        variable.save()

    def delete(self, key, user=None, item=None, item_secondary=None, symmetric=True):
        if key is None:
            raise Exception('Key has to be specified')
        items = [item_secondary, item]
        if symmetric and item is not None and item_secondary is not None:
            items = self._sorted(items)
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

    def number_of_answers(self, user=None, item=None, context=None):
        if item is not None and context is not None:
            raise Exception('Either item or context has to be unspecified')
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': item, 'context_id': context}, False, for_answers=True)
            cursor.execute(
                'SELECT COUNT(id) FROM proso_models_answer WHERE '
                + where, where_params)
            return cursor.fetchone()[0]

    def number_of_correct_answers(self, user=None, item=None, context=None):
        if item is not None and context is not None:
            raise Exception('Either item or context has to be unspecified')
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': item, 'context_id': context}, False, for_answers=True)
            cursor.execute(
                'SELECT COUNT(id) FROM proso_models_answer WHERE item_asked_id = item_answered_id AND '
                + where, where_params)
            return cursor.fetchone()[0]

    def number_of_first_answers(self, user=None, item=None, context=None):
        if item is not None and context is not None:
            raise Exception('Either item or context has to be unspecified')
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': item, 'context_id': context}, False, for_answers=True)
            cursor.execute(
                'SELECT COUNT(1) FROM (SELECT 1 FROM proso_models_answer WHERE '
                + where + ' GROUP BY user_id, item_id) AS t', where_params)
            return cursor.fetchone()[0]

    def last_answer_time(self, user=None, item=None, context=None):
        if item is not None and context is not None:
            raise Exception('Either item or context has to be unspecified')
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': item, 'context_id': context}, False, for_answers=True)
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
            return [fetched.get(i, 0) for i in items]

    @cache_environment_for_item(default=0)
    def number_of_correct_answers_more_items(self, items, user=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': items}, False, for_answers=True)
            cursor.execute(
                'SELECT item_id, COUNT(id) FROM proso_models_answer WHERE item_asked_id = item_answered_id AND '
                + where + ' GROUP BY item_id' + ('' if user is None else ', user_id'),
                where_params)
            fetched = dict(cursor.fetchall())
            return [fetched.get(i, 0) for i in items]

    @cache_environment_for_item(default=0)
    def number_of_first_answers_more_items(self, items, user=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': items}, False, for_answers=True)
            cursor.execute(
                'SELECT item_id, COUNT(1) FROM (SELECT user_id, item_id FROM proso_models_answer WHERE '
                + where + ' GROUP BY user_id, item_id) AS t GROUP BY item_id' + ('' if user is None else ', user_id'),
                where_params)
            fetched = dict(cursor.fetchall())
            return [fetched.get(i, 0) for i in items]
        return 0

    @cache_environment_for_item()
    def last_answer_time_more_items(self, items, user=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': items}, False, for_answers=True)
            cursor.execute(
                'SELECT item_id, MAX(time) FROM proso_models_answer WHERE '
                + where + ' GROUP BY item_id' + ('' if user is None else ', user_id'),
                where_params)
            fetched = dict([(x_d[0], self._ensure_is_datetime(x_d[1])) for x_d in cursor.fetchall()])

            return [fetched.get(i, None) for i in items]

    def shift_time(self, new_time):
        self._time = new_time

    def shift_answers(self, before_answer):
        self._before_answer = before_answer

    def avoid_audit(self, avoid_audit):
        self._avoid_audit = avoid_audit

    def rolling_success(self, user, window_size=10, context=None):
        where, where_params = self._where({'user_id': user, 'context_id': context}, False, for_answers=True)
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT item_asked_id = item_answered_id
                FROM proso_models_answer
                WHERE
                ''' + where +
                '''
                ORDER BY id DESC
                LIMIT %s
                ''', where_params + [window_size])
            fetched = [True if x[0] else False for x in cursor.fetchall()]
            if len(fetched) < window_size:
                return None
            else:
                return sum(fetched) / float(len(fetched))

    def confusing_factor(self, item, item_secondary, user=None):
        return self.confusing_factor_more_items(item, [item_secondary], user=user)[0]

    def confusing_factor_more_items(self, item, items, user=None):
        cached_all = {}
        confusing_factor_cache = cache.get('database_environment__confusing_factor', {})
        for item_secondary in items:
            _items = self._sorted([item, item_secondary])
            cache_key = '{}_{}_{}'.format(_items[0], _items[1], user)
            cached_item = confusing_factor_cache.get(cache_key)
            if cached_item:
                cached_all[item_secondary] = int(cached_item)
        to_find = [i for i in items if i not in list(cached_all.keys())]
        if len(cached_all) != 0:
            LOGGER.debug('cache hit for confusing factor, item {}, {} other items and user {}'.format(item, len(cached_all), user))
        if len(to_find) != 0:
            LOGGER.debug('cache miss for confusing factor, item {}, {} other items and user {}'.format(item, len(to_find), user))
            where, where_params = self._where({
                'item_answered_id': to_find,
                'item_asked_id': to_find,
            }, force_null=False, for_answers=True, conjuction=False)
            user_where, user_params = self._column_comparison('user_id', user, force_null=False)
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    '''
                    SELECT
                        item_asked_id,
                        item_answered_id,
                        COUNT(id) AS confusing_factor
                    FROM
                        proso_models_answer
                    WHERE guess = 0 AND (item_asked_id = %s OR item_asked_id = %s) AND
                    ''' + user_where + ' AND (' + where + ') GROUP BY item_asked_id, item_answered_id', [item, item] + user_params + where_params)
                found = {}
                for item_asked, item_answered, count in cursor:
                    if item_asked == item:
                        found[item_answered] = found.get(item_answered, 0) + count
                    else:
                        found[item_asked] = found.get(item_asked, 0) + count
                for i in to_find:
                    found[i] = found.get(i, 0)
                cache_expiration = get_config('proso_models', 'confusing_factor.cache_expiration', default=24 * 60 * 60)
                for item_secondary, count in found.items():
                    _items = self._sorted([item, item_secondary])
                    cache_key = '{}_{}_{}'.format(_items[0], _items[1], user)
                    confusing_factor_cache[cache_key] = count
                    cached_all[item_secondary] = count
                cache.set('database_environment__confusing_factor', confusing_factor_cache, cache_expiration)
        return [cached_all[i] for i in items]

    def export_values():
        pass

    def export_audit():
        pass

    def _where_single(self, key, user=None, item=None, item_secondary=None, force_null=True, symmetric=True, time_shift=True, for_answers=False):
        if key is None:
            raise Exception('Key has to be specified')
        items = [item_secondary, item]
        if symmetric and item is not None and item_secondary is not None:
            items = self._sorted(items)
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
        if item is None or all([item <= x for x in items]) or not symmetric:
            return self._where(cond_secondary, force_null=force_null, time_shift=time_shift, for_answers=for_answers)
        cond_primary = {
            'key': key,
            'user_id': user,
            'item_primary_id': item,
            'item_secondary_id': items
        }
        if all([item >= x for x in items]):
            return self._where(cond_primary, force_null=force_null, time_shift=time_shift, for_answers=for_answers)
        return self._where({
            'item is primary': cond_primary,
            'item is secondary': cond_secondary
        }, force_null=force_null, time_shift=time_shift, for_answers=for_answers)

    def _where(self, condition, force_null=True, top_most=True, time_shift=True, for_answers=False, conjuction=True):
        if isinstance(condition, tuple):
            result_cond, result_params = self._column_comparison(
                condition[0], condition[1], force_null=force_null)
        elif isinstance(condition, dict):
            conds, params = list(zip(*[self._where(x, force_null, top_most=False, for_answers=for_answers) for x in list(condition.items())]))
            params = [p for ps in params for p in ps]
            operator = ' AND ' if conjuction else ' OR '
            if any([isinstance(x, dict) for x in condition]):
                operator = ' OR '
            result_cond, result_params = operator.join(conds), params
        else:
            raise Exception("Unsupported type of condition:" + str(type(condition)))
        if top_most and not for_answers and self._info_id is not None:
            result_cond = ('(%s) AND (info_id = ? OR info_id IS NULL)' % result_cond)
            result_params = result_params + [self._info_id]
        if top_most and self._time is not None and time_shift:
            result_cond = ('(%s) AND time < ?' % result_cond)
            result_params = result_params + [self._time.strftime('%Y-%m-%d %H:%M:%S')]
        if top_most and self._before_answer:
            if for_answers:
                result_cond = ('(%s) AND id < ?' % result_cond)
                result_params = result_params + [self._before_answer]
            elif not self._avoid_audit:
                result_cond = ('(%s) AND answer_id < ?' % result_cond)
                result_params = result_params + [self._before_answer]
        result_cond = result_cond.replace('?', '%s')
        return result_cond, result_params

    def _column_comparison(self, column, value, force_null=True):
        if isinstance(value, list):
            value = list(set(value))
            contains_null = any([x is None for x in value])
            if contains_null:
                value = [x for x in value if x is not None]
            null_contains_return = (column + ' IS NULL OR ') if contains_null else ''
            if len(value) > 0:
                sorted_values = self._sorted(value)
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

    def _sorted(self, xs):
        inter = sorted([x for x in xs if x is not None])
        return [None] * (len(xs) - len(inter)) + inter
