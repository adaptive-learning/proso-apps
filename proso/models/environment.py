# -*- coding: utf-8 -*-
import abc
import unittest
import datetime
from collections import defaultdict


################################################################################
# API
################################################################################

class Environment(metaclass=abc.ABCMeta):

    """
    This class encapsulates environment for the purpose of modelling.
    """

    def process_answer(self, user, item, asked, answered, time, answer, response_time, guess, **kwargs):
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
            guess (float):
                probability of correct response in case of random answer
        """
        pass

    @abc.abstractmethod
    def audit(self, key, user=None, item=None, item_secondary=None, limit=None, symmetric=True):
        pass

    @abc.abstractmethod
    def get_items_with_values(self, key, item, user=None):
        pass

    @abc.abstractmethod
    def get_items_with_values_more_items(self, key, items, user=None):
        pass

    @abc.abstractmethod
    def read(self, key, user=None, item=None, item_secondary=None, default=None, symmetric=True):
        pass

    @abc.abstractmethod
    def read_more_items(self, key, items, user=None, item=None, default=None, symmetric=True):
        pass

    @abc.abstractmethod
    def write(self, key, value, user=None, item=None, item_secondary=None, time=None, audit=True, symmetric=True, permanent=True, answer=None):
        pass

    @abc.abstractmethod
    def delete(self, key, user=None, item=None, item_secondary=None, symmetric=True):
        pass

    def update(self, key, init_value, update_fun, user=None, item=None, item_secondary=None, time=None, audit=True, symmetric=True, answer=None):
        value = self.read(
            key, user=user, item=item, item_secondary=item_secondary, default=init_value, symmetric=symmetric)
        self.write(
            key, update_fun(value), user=user,
            item=item, item_secondary=item_secondary, time=time, audit=audit, symmetric=symmetric, answer=answer)

    @abc.abstractmethod
    def time(self, key, user=None, item=None, item_secondary=None, symmetric=True):
        pass

    @abc.abstractmethod
    def time_more_items(self, key, items, user=None, item=None, symmetric=True):
        pass

    @abc.abstractmethod
    def export_values(self):
        pass

    @abc.abstractmethod
    def export_audit(self):
        pass

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
    def number_of_answers(self, user=None, item=None, context=None):
        pass

    @abc.abstractmethod
    def number_of_correct_answers(self, user=None, item=None, context=None):
        pass

    @abc.abstractmethod
    def number_of_first_answers(self, user=None, item=None, context=None):
        pass

    @abc.abstractmethod
    def number_of_answers_more_items(self, items, user=None):
        pass

    @abc.abstractmethod
    def number_of_correct_answers_more_items(self, user=None, item=None):
        pass

    @abc.abstractmethod
    def number_of_first_answers_more_items(self, items, user=None):
        pass

    @abc.abstractmethod
    def last_answer_time(self, user=None, item=None, context=None):
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

    @abc.abstractmethod
    def rolling_success(self, user, window_size=10):
        pass


################################################################################
# Implementation
################################################################################

class InMemoryEnvironment(CommonEnvironment):

    NUMBER_OF_ANSWERS = 'number_of_answers'
    NUMBER_OF_CORRECT_ANSWERS = 'number_of_correct_answers'
    NUMBER_OF_FIRST_ANSWERS = 'number_of_first_answers'
    LAST_CORRECTNESS = 'last_correctness'
    CONFUSING_FACTOR = 'confusing_factor'

    def __init__(self):
        # key -> user -> item_primary -> item_secondary -> [(permanent, time, value)]
        self._data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    def process_answer(self, user, item, asked, answered, time, answer, response_time, guess, **kwargs):
        if time is None:
            time = datetime.datetime.now()

        def update_all(key, init_value, update_fun):
            self.update(key, init_value, update_fun, time=time, answer=answer)
            self.update(key, init_value, update_fun, user=user, time=time, answer=answer)
            self.update(key, init_value, update_fun, item=item, time=time, answer=answer)
            self.update(key, init_value, update_fun, user=user, item=item, time=time, answer=answer)
        increment = lambda x: x + 1
        if self.number_of_answers(user=user, item=item) == 0:
            update_all(self.NUMBER_OF_FIRST_ANSWERS, 0, increment)
        update_all(self.NUMBER_OF_ANSWERS, 0, increment)
        if asked == answered:
            update_all(self.NUMBER_OF_CORRECT_ANSWERS, 0, increment)
        self.write(self.LAST_CORRECTNESS, asked == answered, user=user, answer=answer)
        if guess == 0 and asked != answered and answered is not None:
            self.update(self.CONFUSING_FACTOR, 0, increment, item=asked, item_secondary=answered, answer=answer)
            self.update(self.CONFUSING_FACTOR, 0, increment, item=asked, item_secondary=answered, user=user, answer=answer)

    def audit(self, key, user=None, item=None, item_secondary=None, limit=None, symmetric=True):
        items = [item_secondary, item]
        if symmetric and item is not None and item_secondary is not None:
            items.sort()
        found = self._data[key][user][items[1]][items[0]]
        if found and found[0][0]:
            return []
        found = [(x[1], x[3]) for x in found]
        if limit is not None:
            found = found[-limit:]
        found.reverse()
        return found

    def get_items_with_values(self, key, item, user=None):
        return [(i_l[0], i_l[1][-1][3]) for i_l in list(self._data[key][user][item].items())]

    def get_items_with_values_more_items(self, key, items, user=None):
        return [self.get_items_with_values(key, i, user) for i in items]

    def read(self, key, user=None, item=None, item_secondary=None, default=None, symmetric=True):
        found = self._get(key, user=user, item=item, item_secondary=item_secondary, symmetric=symmetric)
        if found:
            return found[3]
        else:
            return default

    def read_more_items(self, key, items, user=None, item=None, default=None, symmetric=True):
        return [self.read(key, user, i, item, default, symmetric) for i in items]

    def write(self, key, value, user=None, item=None, item_secondary=None, time=None, audit=True, symmetric=True, permanent=False, answer=None):
        value = float(value)
        if permanent:
            audit = False
        items = [item_secondary, item]
        if symmetric and item is not None and item_secondary is not None:
            items.sort()
        if time is None:
            time = datetime.datetime.now()
        found = self._data[key][user][items[1]][items[0]]
        if len(found) and found[-1][0] != permanent:
            raise Exception("The variable %s for items %s, %s and user %s changed permamency from %s to %s" % (
                key, item, item_secondary, user, found[-1][0], permanent
            ))
        if audit or not found:
            found.append((permanent, time, answer, value))
        else:
            found[-1] = (permanent, time, answer, value)

    def delete(self, key, user=None, item=None, item_secondary=None, symmetric=True):
        items = [item_secondary, item]
        if symmetric and item is not None and item_secondary is not None:
            items.sort()
        found = self._data[key][user][items[1]][items[0]]
        if len(found) and not found[-1][0]:
            raise Exception("Can't delete variable %s which is not permanent." % key)
        del self._data[key][user][items[1]][items[0]]
        if len(self._data[key][user][items[1]]) == 0:
            del self._data[key][user][items[1]]
            if len(self._data[key][user]) == 0:
                del self._data[key][user]
                if len(self._data[key]):
                    del self._data[key]

    def time(self, key, user=None, item=None, item_secondary=None, symmetric=True):
        found = self._get(key, user=user, item=item, item_secondary=item_secondary, symmetric=symmetric)
        if found:
            return found[1]
        else:
            return None

    def time_more_items(self, key, items, user=None, item=None, symmetric=True):
        return [self.time(key, user, i, item, symmetric) for i in items]

    def number_of_answers(self, user=None, item=None, context=None):
        if context is not None:
            raise Exception('Using context is not supported.')
        return self.read(self.NUMBER_OF_ANSWERS, user=user, item=item, default=0)

    def number_of_correct_answers(self, user=None, item=None, context=None):
        if context is not None:
            raise Exception('Using context is not supported.')
        return self.read(self.NUMBER_OF_CORRECT_ANSWERS, user=user, item=item, default=0)

    def number_of_first_answers(self, user=None, item=None, context=None):
        if context is not None:
            raise Exception('Using context is not supported.')
        return self.read(self.NUMBER_OF_FIRST_ANSWERS, user=user, item=item, default=0)

    def last_answer_time(self, user=None, item=None, context=None):
        if context is not None:
            raise Exception('Using context is not supported.')
        return self.time(self.NUMBER_OF_ANSWERS, user=user, item=item)

    def number_of_answers_more_items(self, items, user=None):
        return self.read_more_items(self.NUMBER_OF_ANSWERS, items, user=user, default=0)

    def number_of_correct_answers_more_items(self, items, user=None):
        return self.read_more_items(self.NUMBER_OF_CORRECT_ANSWERS, items, user=user, default=0)

    def number_of_first_answers_more_items(self, items, user=None):
        return self.read_more_items(self.NUMBER_OF_FIRST_ANSWERS, items, user=user, default=0)

    def last_answer_time_more_items(self, items, user=None):
        return self.time_more_items(self.NUMBER_OF_ANSWERS, items, user=user)

    def rolling_success(self, user, window_size=10, context=None):
        if context is not None:
            raise Exception('Using context is not supported.')
        audit = self.audit(self.LAST_CORRECTNESS, user=user, limit=window_size)
        audit = [x_y[1] for x_y in audit]
        if len(audit) < window_size:
            return None
        else:
            return sum(audit) / float(len(audit))

    def confusing_factor(self, item, item_secondary, user=None):
        return self.read(self.CONFUSING_FACTOR, item=item, item_secondary=item_secondary, user=user, default=0)

    def confusing_factor_more_items(self, item, items, user=None):
        return self.read_more_items(self.CONFUSING_FACTOR, item=item, items=items, user=user, default=0)

    def export_values(self):
        for key, users in self._data.items():
            for user, primaries in users.items():
                for item_primary, secondaries in primaries.items():
                    for item_secondary, values in secondaries.items():
                        if len(values) > 0:
                            permanent, time, answer, value = values[-1]
                            yield (key, user, item_primary, item_secondary, permanent, time, answer, value)

    def export_audit(self):
        for key, users in self._data.items():
            for user, primaries in users.items():
                for item_primary, secondaries in primaries.items():
                    for item_secondary, values in secondaries.items():
                        for permanent, time, answer, value in values:
                            if not permanent:
                                yield (key, user, item_primary, item_secondary, time, answer, value)

    def _get(self, key, user=None, item=None, item_secondary=None, symmetric=True):
        items = [item_secondary, item]
        if symmetric and item is not None and item_secondary is not None:
            items.sort()
        found = self._data[key][user][items[1]][items[0]]
        if found:
            return found[-1]
        else:
            return None


################################################################################
# Tests
################################################################################

class TestEnvironment(unittest.TestCase, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def generate_user(self):
        pass

    @abc.abstractmethod
    def generate_item(self):
        pass

    @abc.abstractmethod
    def generate_environment(self):
        pass

    @abc.abstractmethod
    def generate_answer_id(self):
        pass

    def test_permanent(self):
        items = [self.generate_item() for i in range(3)]
        env = self.generate_environment()
        env.write('key', items[0])
        with self.assertRaises(Exception):
            env.delete('key')
        with self.assertRaises(Exception):
            env.write('key', 1, permament=True)
        env.write('key_permanent', 1, permanent=True)
        env.write('key_permanent', 2, permanent=True)
        self.assertEqual([], env.audit('key_permanent'))
        self.assertEqual(2, env.read('key_permanent'))
        env.delete('key_permanent')
        self.assertEqual([], env.audit('key_permanent'))

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
        for i, v in zip(items, list(range(10))):
            env.write('key', v, item=i)
        for i, v in zip(items, list(range(10, 20))):
            env.write('key', v, user=user, item=i)
        for i, v in zip(items, list(range(20, 30))):
            env.write('key', v, user=user, item=item, item_secondary=i)
        self.assertEqual(list(range(10)), env.read_more_items('key', items))
        self.assertEqual(list(range(10, 20)), env.read_more_items('key', items, user=user))
        self.assertEqual(list(range(20, 30)), env.read_more_items('key', items=items, user=user, item=item))

    def test_audit(self):
        env = self.generate_environment()
        for value in range(100):
            env.write('key', value)
        expected = list(map(float, list(range(100))))
        expected.reverse()
        found = list(list(zip(*env.audit('key')))[1])
        self.assertEqual(expected, found)
        found = list(list(zip(*env.audit('key', limit=10)))[1])
        self.assertEqual(expected[:10], found)


class TestCommonEnvironment(TestEnvironment, metaclass=abc.ABCMeta):

    def test_time(self):
        env = self.generate_environment()
        users = [self.generate_user() for i in range(2)]
        items = [self.generate_item() for i in range(10)]
        self.assertIsNone(env.time('key'))
        self.assertIsNone(env.time('key', user=users[0]))
        self.assertIsNone(env.time('key', user=users[0], item=items[0]))
        self.assertIsNone(env.time('key', user=users[0], item=items[0], item_secondary=items[1]))
        self.assertIsNone(env.time('key', item=items[0]))
        self.assertIsNone(env.time('key', item=items[0], item_secondary=items[1]))
        times = [datetime.datetime.fromtimestamp(i) for i in range(1, 11)]
        env.write('key', 1, time=times[0])
        env.write('key', 1, time=times[1], user=users[0])
        env.write('key', 1, time=times[2], user=users[0], item=items[0])
        env.write('key', 1, time=times[3], user=users[0], item=items[0], item_secondary=items[1])
        env.write('key', 1, time=times[4], item=items[0])
        env.write('key', 1, time=times[5], item=items[0], item_secondary=items[1])
        self.assertEqual(env.time('key'), times[0])
        self.assertEqual(env.time('key', user=users[0]), times[1])
        self.assertEqual(env.time('key', user=users[0], item=items[0]), times[2])
        self.assertEqual(env.time('key', user=users[0], item=items[0], item_secondary=items[1]), times[3])
        self.assertEqual(env.time('key', item=items[0]), times[4])
        self.assertEqual(env.time('key', item=items[0], item_secondary=items[1]), times[5])
        for i, t in zip(items[1:], times):
            env.write('key', 2, item=items[0], item_secondary=i, time=t)
        self.assertEqual(env.time_more_items('key', item=items[0], items=items[1:]), times[:9])

    def test_number_of_answers(self):
        env = self.generate_environment()
        user_1 = self.generate_user()
        user_2 = self.generate_user()
        items = [self.generate_item() for i in range(10)]
        self.assertEqual(env.number_of_answers(), 0)
        self.assertEqual(env.number_of_answers(user=user_1), 0)
        self.assertEqual(env.number_of_answers(user=user_1, item=items[0]), 0)
        self.assertEqual(env.number_of_answers(item=items[0]), 0)
        self.assertEqual([0 for i in items], env.number_of_answers_more_items(items))
        for u in [user_1, user_2]:
            for i in items:
                env.process_answer(u, i, i, i, datetime.datetime.now(), self.generate_answer_id(), 1000, 0)
        self.assertEqual(env.number_of_answers(), 20)
        self.assertEqual(env.number_of_answers(user=user_1), 10)
        self.assertEqual(env.number_of_answers(user=user_1, item=items[0]), 1)
        self.assertEqual(env.number_of_answers(item=items[0]), 2)
        self.assertEqual(env.number_of_answers_more_items(items), [2 for i in items])

    def test_number_of_correct_answers(self):
        env = self.generate_environment()
        user_1 = self.generate_user()
        user_2 = self.generate_user()
        items = [self.generate_item() for i in range(10)]
        self.assertEqual(env.number_of_correct_answers(), 0)
        self.assertEqual(env.number_of_correct_answers(user=user_1), 0)
        self.assertEqual(env.number_of_correct_answers(user=user_1, item=items[0]), 0)
        self.assertEqual(env.number_of_correct_answers(item=items[0]), 0)
        self.assertEqual(env.number_of_first_answers_more_items(items), [0 for i in items])
        for u in [user_1, user_2]:
            for i in items:
                for j in range(10):
                    env.process_answer(u, i, i, i if j < 5 else i + 1, datetime.datetime.now(), self.generate_answer_id(), 1000, 0)
        self.assertEqual(env.number_of_correct_answers(), 100)
        self.assertEqual(env.number_of_correct_answers(user=user_1), 50)
        self.assertEqual(env.number_of_correct_answers(user=user_1, item=items[0]), 5)
        self.assertEqual(env.number_of_correct_answers(item=items[0]), 10)
        self.assertEqual(env.number_of_correct_answers_more_items(items), [10 for i in items])

    def test_number_of_first_answers(self):
        env = self.generate_environment()
        user_1 = self.generate_user()
        user_2 = self.generate_user()
        items = [self.generate_item() for i in range(10)]
        self.assertEqual(env.number_of_first_answers(), 0)
        self.assertEqual(env.number_of_first_answers(user=user_1), 0)
        self.assertEqual(env.number_of_first_answers(user=user_1, item=items[0]), 0)
        self.assertEqual(env.number_of_first_answers(item=items[0]), 0)
        self.assertEqual(env.number_of_first_answers_more_items(items), [0 for i in items])
        for u in [user_1, user_2]:
            for i in items:
                for j in range(10):
                    env.process_answer(u, i, i, i, datetime.datetime.now(), self.generate_answer_id(), 1000, 0)
        self.assertEqual(env.number_of_first_answers(), 20)
        self.assertEqual(env.number_of_first_answers(user=user_1), 10)
        self.assertEqual(env.number_of_first_answers(user=user_1, item=items[0]), 1)
        self.assertEqual(env.number_of_first_answers(item=items[0]), 2)
        self.assertEqual(env.number_of_first_answers_more_items(items), [2 for i in items])

    def test_symmetry(self):
        env = self.generate_environment()
        items = [self.generate_item() for i in range(2)]
        env.write(key='test_symmetric', value=1, item=items[0], item_secondary=items[1])
        env.write(
            key='test_assymetric', value=1, item=items[0],
            item_secondary=items[1], symmetric=False)
        self.assertEqual(
            env.read(key='test_symmetric', item=items[1], item_secondary=items[0]), 1)
        self.assertIsNone(
            env.read(key='test_assymetric', item=items[1], item_secondary=items[0]))

    def test_last_answer_time(self):
        env = self.generate_environment()
        user_1 = self.generate_user()
        user_2 = self.generate_user()
        items = [self.generate_item() for i in range(10)]
        self.assertIsNone(env.last_answer_time())
        self.assertIsNone(env.last_answer_time(user=user_1))
        self.assertIsNone(env.last_answer_time(user=user_1, item=items[0]))
        self.assertIsNone(env.last_answer_time(item=items[0]))
        self.assertEqual(env.last_answer_time_more_items(items), [None for i in items])
        for u in [user_1, user_2]:
            for i in items:
                for j in range(10):
                    env.process_answer(u, i, i, i, datetime.datetime.now(), self.generate_answer_id(), 1000, 0)
        self.assertIsNotNone(env.number_of_first_answers())
        self.assertIsNotNone(env.number_of_first_answers(user=user_1))
        self.assertIsNotNone(env.number_of_first_answers(user=user_1, item=items[0]))
        self.assertIsNotNone(env.number_of_first_answers(item=items[0]))
        self.assertNotEqual(env.number_of_first_answers_more_items(items), [None for i in items])

    def test_rolling_success(self):
        env = self.generate_environment()
        user_1 = self.generate_user()
        user_2 = self.generate_user()
        items = [self.generate_item() for i in range(10)]
        self.assertIsNone(env.rolling_success(user_1))
        self.assertIsNone(env.rolling_success(user_2))
        diff = 0
        for u in [user_1, user_2]:
            for i in items:
                for j in range(10):
                    env.process_answer(u, i, i, i + diff, datetime.datetime.now(), self.generate_answer_id(), 1000, 0)
            diff += 1
        self.assertEqual(env.rolling_success(user_1), 1.0)
        self.assertEqual(env.rolling_success(user_2), 0.0)

    def test_confusing_factor(self):
        env = self.generate_environment()
        user_1 = self.generate_user()
        user_2 = self.generate_user()
        items = [self.generate_item() for i in range(10)]
        self.assertEqual(env.confusing_factor(item=items[0], item_secondary=items[1]), 0)
        self.assertEqual(env.confusing_factor(item=items[0], item_secondary=items[1], user=user_1), 0)
        for i in items:
            for guess in [0, 1. / 3, 1. / 5]:
                env.process_answer(user_1, items[0], items[0], i, datetime.datetime.now(), self.generate_answer_id(), 1000, guess)
        for i in items:
            for guess in [0, 1. / 3, 1. / 5]:
                env.process_answer(user_2, i, i, i, datetime.datetime.now(), self.generate_answer_id(), 1000, guess)
        self.assertEqual(env.confusing_factor(item=items[0], item_secondary=items[1]), 1)
        self.assertEqual(env.confusing_factor(item=items[0], item_secondary=items[1], user=user_1), 1)
        self.assertEqual(env.confusing_factor(item=items[0], item_secondary=items[1], user=user_2), 0)
        self.assertEqual(env.confusing_factor(item=items[2], item_secondary=items[3]), 0)

    def test_get_items_with_values(self):
        env = self.generate_environment()
        users = [self.generate_user() for i in range(2)]
        items = [self.generate_item() for i in range(2)]
        env.write('parent', 10, user=users[0], item=items[0], item_secondary=items[1], symmetric=False)
        env.write('parent', 20, item=items[1], item_secondary=items[0], symmetric=False)
        self.assertEqual(env.get_items_with_values('parent', user=users[0], item=items[0]), [(items[1], 10)])
        self.assertEqual(env.get_items_with_values('parent', user=users[0], item=items[1]), [])
        self.assertEqual(env.get_items_with_values('parent', user=users[1], item=items[0]), [])
        self.assertEqual(env.get_items_with_values('parent', item=items[1]), [(items[0], 20)])
        self.assertEqual(env.get_items_with_values('parent', user=users[0], item=items[1]), [])

    def test_get_items_with_values_more_items(self):
        env = self.generate_environment()
        users = [self.generate_user() for i in range(2)]
        items = [self.generate_item() for i in range(2)]
        env.write('parent', 10, user=users[0], item=items[0], item_secondary=items[1], symmetric=False)
        env.write('parent', 20, item=items[1], item_secondary=items[0], symmetric=False)
        self.assertEqual(
            env.get_items_with_values_more_items('parent', user=users[0], items=items),
            [[(items[1], 10)], []])
        self.assertEqual(
            env.get_items_with_values_more_items('parent', items=items),
            [[], [(items[0], 20)]])
