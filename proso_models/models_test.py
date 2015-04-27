from django.contrib.auth.models import User
from models import DatabaseEnvironment, EnvironmentInfo
from models import Item
import django.test as test
from django.conf import settings
import proso.models.environment as environment
from proso.django.config import get_config
from proso_common.models import Config


class DatabaseEnvironmentTest(test.TestCase, environment.TestCommonEnvironment):

    _user = 0

    @staticmethod
    def setUpClass():
        settings.DEBUG = True
        config = Config.objects.from_content(get_config('proso_models', 'predictive_model', default={}))
        EnvironmentInfo.objects.get_or_create(config=config, status=EnvironmentInfo.STATUS_ACTIVE, revision=0)

    def generate_item(self):
        item = Item()
        item.save()
        return item.id

    def generate_user(self):
        self._user += 1
        user = User(username=str(self._user))
        user.save()
        return user.id

    def generate_environment(self):
        return DatabaseEnvironment()
