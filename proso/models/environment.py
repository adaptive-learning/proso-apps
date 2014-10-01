# -*- coding: utf-8 -*-
import abc
import unittest
import datetime


################################################################################
# API
################################################################################

class Environment:

    """
    This class encapsulates environment for the purpose of modelling.
    """

    __metaclass__ = abc.ABCMeta

    def process_answer(self, user, item, asked, answered, time, response_time=None, **kwargs):
        """
        This method is used during the answer streaming and is called after the
        predictive model for each answer.

        Args:
            user (int):
                identifier of ther user answering the question
            asked (int):
                identifier of the asked item
            answered (int):
                identifier of the answered item or None if the user answered
                "I don't know"
            response_time (int)
                time the answer took in milliseconds
            time (datetime.datetime)
                time when the user answered the question
        """
        pass

    @abc.abstractmethod
    def audit(self, key, user=None, item=None, item_secondary=None, limit=None):
        pass

    @abc.abstractmethod
    def read(self, key, user=None, item=None, item_secondary=None, default=None):
        pass

    @abc.abstractmethod
    def read_more_items(self, key, items, user=None, item=None, default=None):
        pass

    @abc.abstractmethod
    def write(self, key, value, user=None, item=None, item_secondary=None, time=None, audit=True):
        pass

    def update(self, key, init_value, update_fun, user=None, item=None, item_secondary=None, time=None, audit=True):
        value = self.read(
            key, user=user, item=item, item_secondary=item_secondary, default=init_value)
        self.write(
            key, update_fun(value), user=user,
            item=item, item_secondary=item_secondary, time=time, audit=audit)

    def flush(self):
        """
        This method is called to enforce persistence of the data. This is
        useful mainly for interaction with database where it is not efficient
        to touch database for each answer. When your environment is only an in
        memery implementation, you can leave this method as it is.
        """
        pass


class CommonEnvironment(Environment):

    @abc.abstractmethod
    def number_of_answers(self, user=None, item=None):
        pass

    @abc.abstractmethod
    def number_of_first_answers(self, user=None, item=None):
        pass

    @abc.abstractmethod
    def number_of_answers_more_items(self, items, user=None):
        pass

    @abc.abstractmethod
    def number_of_first_answers_more_items(self, items, user=None):
        pass

    @abc.abstractmethod
    def last_answer_time(self, user=None, item=None):
        pass

    @abc.abstractmethod
    def last_answer_time_more_items(self, items, user=None):
        pass

    @abc.abstractmethod
    def confusing_factor(self, item, item_secondary, user=None):
        pass

    @abc.abstractmethod
    def confusing_factor_more_items(self, item, items, user=None):
        pass


################################################################################
# Implementation
################################################################################

class InMemoryEnvironment(CommonEnvironment):

    NUMBER_OF_ANSWERS = 'number_of_answers'
    NUMBER_OF_FIRST_ANSWERS = 'number_of_first_answers'
    LAST_ANSWER_TIME = 'last_answer_time'
    LAST_CORRECTNESS = 'last_correctness'
    CONFUSING_FACTOR = 'confusing_factor'

    def __init__(self):
        self._audit = {}
        self._state = {}

    def process_answer(self, user, item, asked, answered, time, response_time=None, **kwargs):
        if time is None:
            time = datetime.datetime.now()

        def update_all(key, init_value, update_fun):
            self.update(key, init_value, update_fun, time=time)
            self.update(key, init_value, update_fun, user=user, time=time)
            self.update(key, init_value, update_fun, item=item, time=time)
            self.update(key, init_value, update_fun, user=user, item=item, time=time)
        increment = lambda x: x + 1
        if self.number_of_answers(user=user, item=item) == 0:
            update_all(self.NUMBER_OF_FIRST_ANSWERS, 0, increment)
        update_all(self.NUMBER_OF_ANSWERS, 0, increment)
        update_all(self.LAST_ANSWER_TIME, time, lambda x: time)
        self.write(self.LAST_CORRECTNESS, asked == answered, user=user)
        if asked != answered and answered is not None:
            self.update(self.CONFUSING_FACTOR, 0, increment, item=asked, item_secondary=answered)
            self.update(self.CONFUSING_FACTOR, 0, increment, item=asked, item_secondary=answered, user=user)

    def audit(self, key, user=None, item=None, item_secondary=None, limit=None):
        audit = self._audit.get(self._key(key, user, item, item_secondary), [])
        if limit is not None:
            audit = audit[-limit:]
        return audit

    def read(self, key, user=None, item=None, item_secondary=None, default=None):
        return self._state.get(self._key(key, user, item, item_secondary), default)

    def read_more_items(self, key, items, user=None, item=None, default=None):
        return map(
            lambda i: self.read(key, user, i, item, default),
            items)

    def write(self, key, value, user=None, item=None, item_secondary=None, time=None, audit=True):
        _key = self._key(key, user, item, item_secondary)
        if time is None:
            time = datetime.datetime.now()
        if audit:
            previous_audit = self._audit.get(_key, [])
            previous_audit.append((time, value))
            self._audit[_key] = previous_audit
        self._state[_key] = value

    def number_of_answers(self, user=None, item=None):
        return self.read(self.NUMBER_OF_ANSWERS, user=user, item=item, default=0)

    def number_of_first_answers(self, user=None, item=None):
        return self.read(self.NUMBER_OF_FIRST_ANSWERS, user=user, item=item, default=0)

    def last_answer_time(self, user=None, item=None):
        return self.read(self.LAST_ANSWER_TIME, user=user, item=item)

    def number_of_answers_more_items(self, items, user=None):
        return self.read_more_items(self.NUMBER_OF_ANSWERS, items, user=user, default=0)

    def number_of_first_answers_more_items(self, items, user=None):
        return self.read_more_items(self.NUMBER_OF_FIRST_ANSWERS, items, user=user, default=0)

    def last_answer_time_more_items(self, items, user=None):
        return self.read_more_items(self.LAST_ANSWER_TIME, items, user=user)

    def rolling_success(self, user, window_size=10):
        audit = self.audit(self.LAST_CORRECTNESS, user=user, limit=window_size)
        audit = map(lambda (x, y): y, audit)
        if len(audit) == 0:
            return 1.0
        else:
            return sum(audit) / float(len(audit))

    def confusing_factor(self, item, item_secondary, user=None):
        return self.read(self.CONFUSING_FACTOR, item=item, item_secondary=item_secondary, user=user, default=0)

    def confusing_factor_more_items(self, item, items, user=None):
        return self.read_more_items(self.CONFUSING_FACTOR, item=item, items=items, user=user, default=0)

    def _key(self, key, user, item, item_secondary):
        items = sorted([item, item_secondary])
        return (key, user, items[1], items[0])


################################################################################
# Tests
################################################################################

class TestEnvironment(unittest.TestCase):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def generate_user(self):
        pass

    @abc.abstractmethod
    def generate_item(self):
        pass

    @abc.abstractmethod
    def generate_environment(self):
        pass

    def test_write_and_read(self):
        env = self.generate_environment()
        user = self.generate_user()
        item = self.generate_item()
        item_secondary = self.generate_item()
        env.write('key', 666)
        env.write('key', 667, user=user)
        env.write('key', 668, item=item)
        env.write('key', 669, user=user, item=item)
        env.write('key', 670, item=item, item_secondary=item_secondary)
        env.write('key', 671, user=user, item=item, item_secondary=item_secondary)
        self.assertEqual(666, env.read('key'))
        self.assertEqual(667, env.read('key', user=user))
        self.assertEqual(668, env.read('key', item=item))
        self.assertEqual(669, env.read('key', user=user, item=item))
        self.assertEqual(670, env.read('key', item=item, item_secondary=item_secondary))
        self.assertEqual(671, env.read('key', user=user, item=item, item_secondary=item_secondary))

    def test_read_more_items(self):
        env = self.generate_environment()
        item = self.generate_item()
        items = [self.generate_item() for i in range(10)]
        user = self.generate_user()
        for i, v in zip(items, range(10)):
            env.write('key', v, item=i)
        for i, v in zip(items, range(10, 20)):
            env.write('key', v, user=user, item=i)
        for i, v in zip(items, range(20, 30)):
            env.write('key', v, user=user, item=item, item_secondary=i)
        self.assertEqual(range(10), env.read_more_items('key', items))
        self.assertEqual(range(10, 20), env.read_more_items('key', items, user=user))
        self.assertEqual(range(20, 30), env.read_more_items('key', items=items, user=user, item=item))

    def test_audit(self):
        env = self.generate_environment()
        for value in range(100):
            env.write('key', value)
        expected = map(float, range(100))
        found = list(zip(*env.audit('key'))[1])
        self.assertEqual(expected, found)


class TestCommonEnvironment(TestEnvironment):

    __metaclass__ = abc.ABCMeta

    def test_number_of_answers(self):
        env = self.generate_environment()
        user_1 = self.generate_user()
        user_2 = self.generate_user()
        items = [self.generate_item() for i in range(10)]
        self.assertEqual(0, env.number_of_answers())
        self.assertEqual(0, env.number_of_answers(user=user_1))
        self.assertEqual(0, env.number_of_answers(user=user_1, item=items[0]))
        self.assertEqual(0, env.number_of_answers(item=items[0]))
        self.assertEqual([0 for i in items], env.number_of_answers_more_items(items))
        for u in [user_1, user_2]:
            for i in items:
                env.process_answer(u, i, i, i, datetime.datetime.now(), 1000)
        self.assertEqual(20, env.number_of_answers())
        self.assertEqual(10, env.number_of_answers(user=user_1))
        self.assertEqual(1, env.number_of_answers(user=user_1, item=items[0]))
        self.assertEqual(2, env.number_of_answers(item=items[0]))
        self.assertEqual([2 for i in items], env.number_of_answers_more_items(items))

    def test_number_of_first_answers(self):
        env = self.generate_environment()
        user_1 = self.generate_user()
        user_2 = self.generate_user()
        items = [self.generate_item() for i in range(10)]
        self.assertEqual(0, env.number_of_first_answers())
        self.assertEqual(0, env.number_of_first_answers(user=user_1))
        self.assertEqual(0, env.number_of_first_answers(user=user_1, item=items[0]))
        self.assertEqual(0, env.number_of_first_answers(item=items[0]))
        self.assertEqual([0 for i in items], env.number_of_first_answers_more_items(items))
        for u in [user_1, user_2]:
            for i in items:
                for j in range(10):
                    env.process_answer(u, i, i, i, datetime.datetime.now(), 1000)
        self.assertEqual(20, env.number_of_first_answers())
        self.assertEqual(10, env.number_of_first_answers(user=user_1))
        self.assertEqual(1, env.number_of_first_answers(user=user_1, item=items[0]))
        self.assertEqual(2, env.number_of_first_answers(item=items[0]))
        self.assertEqual([2 for i in items], env.number_of_first_answers_more_items(items))

    def test_last_answer_time(self):
        env = self.generate_environment()
        user_1 = self.generate_user()
        user_2 = self.generate_user()
        items = [self.generate_item() for i in range(10)]
        self.assertEqual(None, env.last_answer_time())
        self.assertEqual(None, env.last_answer_time(user=user_1))
        self.assertEqual(None, env.last_answer_time(user=user_1, item=items[0]))
        self.assertEqual(None, env.last_answer_time(item=items[0]))
        self.assertEqual([None for i in items], env.last_answer_time_more_items(items))
        for u in [user_1, user_2]:
            for i in items:
                for j in range(10):
                    env.process_answer(u, i, i, i, datetime.datetime.now())
        self.assertIsNotNone(env.number_of_first_answers())
        self.assertIsNotNone(env.number_of_first_answers(user=user_1))
        self.assertIsNotNone(env.number_of_first_answers(user=user_1, item=items[0]))
        self.assertIsNotNone(env.number_of_first_answers(item=items[0]))
        self.assertNotEqual([None for i in items], env.number_of_first_answers_more_items(items))

    def test_rolling_success(self):
        env = self.generate_environment()
        user_1 = self.generate_user()
        user_2 = self.generate_user()
        items = [self.generate_item() for i in range(10)]
        self.assertEqual(1.0, env.rolling_success(user_1))
        self.assertEqual(1.0, env.rolling_success(user_2))
        diff = 0
        for u in [user_1, user_2]:
            for i in items:
                for j in range(10):
                    env.process_answer(u, i, i, i + diff, datetime.datetime.now())
            diff += 1
        self.assertEqual(1.0, env.rolling_success(user_1))
        self.assertEqual(0.0, env.rolling_success(user_2))

    def test_confusing_factor(self):
        env = self.generate_environment()
        user_1 = self.generate_user()
        user_2 = self.generate_user()
        items = [self.generate_item() for i in range(10)]
        self.assertEqual(0, env.confusing_factor(item=items[0], item_secondary=items[1]))
        self.assertEqual(0, env.confusing_factor(item=items[0], item_secondary=items[1], user=user_1))
        for i in items:
            env.process_answer(user_1, items[0], items[0], i, datetime.datetime.now())
        for i in items:
            env.process_answer(user_2, i, i, i, datetime.datetime.now())
        self.assertEqual(1, env.confusing_factor(item=items[0], item_secondary=items[1]))
        self.assertEqual(1, env.confusing_factor(item=items[0], item_secondary=items[1], user=user_1))
        self.assertEqual(0, env.confusing_factor(item=items[0], item_secondary=items[1], user=user_2))
        self.assertEqual(0, env.confusing_factor(item=items[2], item_secondary=items[3]))
