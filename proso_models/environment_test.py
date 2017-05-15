from .environment import DatabaseEnvironment
from .models import Item
from django.conf import settings
from django.contrib.auth.models import User
import datetime
import django.test as test
import proso.models.environment as environment


class DatabaseEnvironmentTest(test.TestCase, environment.TestCommonEnvironment):

    _user = 0

    @classmethod
    def setUpClass(cls):
        super(DatabaseEnvironmentTest, cls).setUpClass()
        settings.DEBUG = True

    def generate_item(self):
        item = Item()
        item.save()
        return item.id

    def generate_user(self):
        self._user += 1
        user = User(username=str(self._user))
        user.save()
        return user.id

    def generate_answer_id(self):
        return None

    def generate_environment(self):
        return DatabaseEnvironment()

    def test_rolling_success(self):
        env = self.generate_environment()
        user_1 = self.generate_user()
        user_2 = self.generate_user()
        items = [self.generate_item() for i in range(5)]
        self.assertIsNone(env.rolling_success(user_1))
        self.assertIsNone(env.rolling_success(user_2))
        diff = 0
        for u in [user_1, user_2]:
            for i in items:
                for j in range(5):
                    env.process_answer(u, i, i, i + diff, datetime.datetime.now(), self.generate_answer_id(), 1000, 0)
            diff += 1
        self.assertEqual(env.rolling_success(user_1), 1.0)
        self.assertEqual(env.rolling_success(user_2), 0.0)
