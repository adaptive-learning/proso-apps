from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from proso.models.environment import CommonEnvironment, InMemoryEnvironment
from datetime import datetime
from contextlib import closing
from django.db import connection
from django.conf import settings
import re
import os.path
import proso.util


################################################################################
# getters
################################################################################

def get_environment():
    return proso.util.instantiate(settings.PROSO_ENVIRONMENT)


def get_predictive_model():
    return proso.util.instantiate(settings.PROSO_PREDICTIVE_MODEL)


def get_recommendation():
    return proso.util.instantiate(settings.PROSO_RECOMMENDATION, [get_predictive_model()])


################################################################################
# Environment
################################################################################

class InMemoryDatabaseFlushEnvironment(InMemoryEnvironment):

    def flush(self):
        to_skip = [
            self.NUMBER_OF_ANSWERS, self.NUMBER_OF_FIRST_ANSWERS,
            self.LAST_ANSWER_TIME, self.LAST_CORRECTNESS
        ]
        filename_audit = os.path.join(settings.DATA_DIR, 'environment_flush_audit.csv')
        filename_variable = os.path.join(settings.DATA_DIR, 'environment_flush_variable.csv')
        with open(filename_audit, 'w') as file_audit:
            for (key, u, i_p, i_s), values in self._audit.iteritems():
                if key in to_skip:
                    continue
                for (t, v) in values:
                    file_audit.write(
                        ('%s,%s,%s,%s,%s,%s\n' % (key, u, i_p, i_s, t.strftime('%Y-%m-%d %H:%M:%S'), v)).replace('None', ''))
        with open(filename_variable, 'w') as file_variable:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for (key, u, i_p, i_s), v in self._state.iteritems():
                if key in to_skip:
                    continue
                file_variable.write(
                    ('%s,%s,%s,%s,%s,%s,%s\n' % (key, u, i_p, i_s, v, 0, current_time)).replace('None', ''))
        print 'DELETE FROM proso_models_audit;'
        print 'DELETE FROM proso_models_variable;'
        print "\copy proso_models_audit (key, user_id, item_primary_id, item_secondary_id, time, value) FROM '%s' WITH (FORMAT csv);" % filename_audit
        print "\copy proso_models_variable (key, user_id, item_primary_id, item_secondary_id, value, audit, updated) FROM '%s' WITH (FORMAT csv);" % filename_variable


class DatabaseEnvironment(CommonEnvironment):

    time = None

    def process_answer(self, user, item, asked, answered, time, response_time=None, **kwargs):
        answer = Answer(
            user_id=user,
            item_id=item,
            item_asked_id=asked,
            item_answered_id=answered,
            time=time,
            response_time=response_time)
        answer.save()

    def audit(self, key, user=None, item=None, item_secondary=None, limit=100000):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where_single(key, user, item, item_secondary)
            cursor.execute(
                'SELECT time, value FROM proso_models_audit WHERE '
                + where +
                ' ORDER BY time DESC LIMIT %s',
                where_params + [limit])
            result = cursor.fetchall()
            map(lambda (d, v): (self._ensure_is_datetime(d), v), result)
            return result

    def read(self, key, user=None, item=None, item_secondary=None, default=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where_single(key, user, item, item_secondary)
            if self.time is None:
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

    def read_more_items(self, key, items, user=None, item=None, default=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where_more_items(key, items, user, item)
            if self.time is None:
                cursor.execute(
                    'SELECT item_primary_id, item_secondary_id, value FROM proso_models_variable WHERE '
                    + where,
                    where_params)
                result = cursor.fetchall()
            else:
                cursor.execute(
                    '''SELECT DISTINCT ON
                        (key, item_primary_id, item_secondary_id, user_id, item_primary_id)
                        item_secondary_id, value FROM proso_models_audit WHERE
                    ''' + where +
                    ' ORDER BY time',
                    where_params)
                result = map(lambda (w, x, y, z): (x, y, z), cursor.fetchall())
            if item is None:
                result = map(lambda (x, y, z): (x, z), result)
            else:
                result = map(lambda (x, y, z): (x, z) if y == item else (y, z), result)
            result = dict(result)
            return map(lambda key: result.get(key, default), items)

    def write(self, key, value, user=None, item=None, item_secondary=None, time=None, audit=True):
        if key is None:
            raise Exception('Key has to be specified')
        if value is None:
            raise Exception('Value has to be specified')
        items = sorted([item, item_secondary])
        data = {
            'user_id': user,
            'item_primary_id': items[1],
            'item_secondary_id': items[0],
            'key': key
        }
        try:
            variable = Variable.objects.get(**data)
        except Variable.DoesNotExist:
            variable = Variable(**data)
        variable.value = value
        variable.audit = audit
        variable.updated = datetime.now() if time is None else time
        variable.save()

    def number_of_answers(self, user=None, item=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': item}, False)
            cursor.execute(
                'SELECT COUNT(id) FROM proso_models_answer WHERE '
                + where, where_params)
            return cursor.fetchone()[0]

    def number_of_first_answers(self, user=None, item=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': item}, False)
            cursor.execute(
                'SELECT COUNT(1) FROM (SELECT 1 FROM proso_models_answer WHERE '
                + where + ' GROUP BY user_id, item_id) AS t', where_params)
            return cursor.fetchone()[0]

    def last_answer_time(self, user=None, item=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': item}, False)
            cursor.execute(
                'SELECT MAX(time) FROM proso_models_answer WHERE '
                + where, where_params)
            return self._ensure_is_datetime(cursor.fetchone()[0])

    def number_of_answers_more_items(self, items, user=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': items}, False)
            cursor.execute(
                'SELECT item_id, COUNT(id) FROM proso_models_answer WHERE '
                + where + ' GROUP BY item_id' + ('' if user is None else ', user_id'),
                where_params)
            fetched = dict(cursor.fetchall())
            return map(lambda i: fetched.get(i, 0), items)

    def number_of_first_answers_more_items(self, items, user=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': items}, False)
            cursor.execute(
                'SELECT item_id, COUNT(1) FROM (SELECT user_id, item_id FROM proso_models_answer WHERE '
                + where + ' GROUP BY user_id, item_id) AS t GROUP BY item_id' + ('' if user is None else ', user_id'),
                where_params)
            fetched = dict(cursor.fetchall())
            return map(lambda i: fetched.get(i, 0), items)
        return 0

    def last_answer_time_more_items(self, items, user=None):
        with closing(connection.cursor()) as cursor:
            where, where_params = self._where({'user_id': user, 'item_id': items}, False)
            cursor.execute(
                'SELECT item_id, MAX(time) FROM proso_models_answer WHERE '
                + where + ' GROUP BY item_id' + ('' if user is None else ', user_id'),
                where_params)
            fetched = dict(map(lambda (x, d): (x, self._ensure_is_datetime(d)), cursor.fetchall()))

            return map(lambda i: fetched.get(i, None), items)

    def shift_time(self, new_time):
        self.time = new_time

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
            fetched = map(lambda x: x[0], cursor.fetchall())
            if len(fetched) == 0:
                return 1.0
            else:
                return sum(fetched) / float(len(fetched))

    def confusing_factor(self, item, item_secondary, user=None):
        pass

    def confusing_factor_more_items(self, item, items, user=None):
        pass

    def _where_single(self, key, user=None, item=None, item_secondary=None):
        if key is None:
            raise Exception('Key has to be specified')
        items = sorted([item, item_secondary])
        return self._where({
            'user_id': user,
            'item_primary_id': items[1],
            'item_secondary_id': items[0],
            'key': key})

    def _where_more_items(self, key, items, user=None, item=None, default=None):
        if key is None:
            raise Exception('Key has to be specified')
        cond_secondary = {
            'key': key,
            'user_id': user,
            'item_primary_id': items,
            'item_secondary_id': item
        }
        if item is None or all(map(lambda x: item <= x, items)):
            return self._where(cond_secondary)
        cond_primary = {
            'key': key,
            'user_id': user,
            'item_primary_id': item,
            'item_secondary_id': items
        }
        if all(map(lambda x: item >= x, items)):
            return self._where(cond_primary)
        return self._where({
            'item is primary': cond_primary,
            'item is secondary': cond_secondary
        })

    def _where(self, condition, force_null=True, top_most=True):
        if isinstance(condition, tuple):
            result_cond, result_params = self._column_comparison(condition[0], condition[1], force_null=force_null)
        elif isinstance(condition, dict):
            conds, params = zip(*map(lambda x: self._where(x, force_null, top_most=False), condition.items()))
            params = [p for ps in params for p in ps]
            operator = ' AND '
            if any(map(lambda x: isinstance(x, dict), condition)):
                operator = ' OR '
            result_cond, result_params = operator.join(conds), params
        else:
            raise Exception("Unsupported type of condition:" + str(type(condition)))
        if top_most and self.time is not None:
            result_cond = ('(%s) AND time < ?' % result_cond).replace('?', '%s')
            result_params = result_params + [self.time.strftime('%Y-%m-%d %H:%M:%S')]
        return result_cond, result_params

    def _column_comparison(self, column, value, force_null=True):
        if isinstance(value, list):
            value = filter(lambda x: x is not None, value)
            if len(value) > 0:
                return column + ' IN (' + ','.join(['%s' for i in value]) + ')', value
            elif force_null:
                return column + ' IS NULL', []
            else:
                return 'TRUE', []
        elif value is not None:
            return column + ' = %s', [value]
        elif force_null:
            return column + ' IS NULL', []
        else:
            return 'TRUE', []

    def _ensure_is_datetime(self, value):
        if isinstance(value, datetime):
            return value
        else:
            matched = re.match(r'([\d -\:]*)\.\d+', value)
            if matched is not None:
                value = matched.groups()[0]
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')


################################################################################
# Models
################################################################################

class Item(models.Model):
    pass

    class Meta:
        app_label = 'proso_models'


class Answer(models.Model):

    user = models.ForeignKey(User)
    item = models.ForeignKey(Item, related_name='item_answers')
    item_asked = models.ForeignKey(Item, related_name='item_asked_answers')
    item_answered = models.ForeignKey(
        Item,
        null=True,
        blank=True,
        default=None,
        related_name='item_answered_answers')
    time = models.DateTimeField(default=datetime.now)
    response_time = models.IntegerField(default=0)

    class Meta:
        app_label = 'proso_models'


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
    key = models.CharField(max_length=50)
    value = models.FloatField()
    audit = models.BooleanField()
    updated = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return str({
            'user': self.user_id,
            'key': self.key,
            'item_primary': self.item_primary_id,
            'item_secondary': self.item_secondary_id,
            'value': self.value
        })

    class Meta:
        app_label = 'proso_models'
        unique_together = ('key', 'user', 'item_primary', 'item_secondary')
        index_together = [
            ['key', 'user'],
            ['key', 'item_primary'],
            ['key', 'user', 'item_primary'],
            ['key', 'user', 'item_primary', 'item_secondary']
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

    class Meta:
        app_label = 'proso_models'
        unique_together = ('key', 'user', 'item_primary', 'item_secondary')
        index_together = [
            ['key', 'user'],
            ['key', 'item_primary'],
            ['key', 'user', 'item_primary'],
            ['key', 'user', 'item_primary', 'item_secondary']
        ]


################################################################################
# Signals
################################################################################

@receiver(pre_save, sender=Variable)
def sort_items(sender, instance, **kwargs):
    if instance.item_primary is None:
        instance.item_primary = instance.item_secondary
        instance.item_secondary = None
    elif instance.item_secondary is not None:
        if instance.item_primary.pk < instance.item_secondary.pk:
            backup = instance.item_primary
            instance.item_primary = instance.item_secondary
            instance.item_secondary = backup


@receiver(post_save, sender=Answer)
def update_predictive_model(sender, instance, **kwargs):
    environment = get_environment()
    predictive_model = get_predictive_model()
    predictive_model.predict_and_update(
        environment,
        instance.user.id,
        instance.item_id,
        instance.item_asked_id == instance.item_answered_id,
        instance.time,
        item_answered=instance.item_answered_id,
        item_asked=instance.item_asked_id)


@receiver(post_save, sender=Variable)
def log_audit(sender, instance, **kwargs):
    if instance.audit:
        audit = Audit(
            user=instance.user,
            item_primary=instance.item_primary,
            key=instance.key,
            value=instance.value,
            time=instance.updated)
        audit.save()
