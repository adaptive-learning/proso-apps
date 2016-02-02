from django.contrib.auth.models import User
from .models import DatabaseEnvironment
from .models import Item
import django.test as test
from django.conf import settings
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
