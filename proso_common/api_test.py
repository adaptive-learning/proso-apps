from django.contrib.auth.models import User
from django.core.management import call_command
from proso.django.config import reset_overridden
from proso.django.test import TestCase
import json

from testproject import settings


class CommonAPITest(TestCase):

    @classmethod
    def setUpClass(cls):
        super(CommonAPITest, cls).setUpClass()
        User.objects.create_superuser('admin', 'admin@test.com', 'admin')

    def tearDown(self):
        self.client.logout()
        reset_overridden()

    def testConfig(self):
        response = self.client.get('/common/config/?config.my.super.property=true')
        self.assertEqual(response.status_code, 200, 'The configuration is available.')
        self.assertFalse('my' in json.loads(response.content.decode("utf-8"))['data'], "Non-staff user can't override configuration properties.")
        self.client.login(username='admin', password='admin')
        response = self.client.get('/common/config/?config.my.super.property=true')
        self.assertEqual(response.status_code, 200, 'The configuration is available.')
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))['data']['my']['super']['property'],
            True,
            'Staff user can override configuration properties'
        )

    def testAnalysis(self):
        call_command('table2csv')
        call_command('custom_export')
        response = self.client.get('/common/csv/')
        self.assertEqual(response.status_code, 401, "Non-staff user can't get CSV files.")
        self.client.login(username='admin', password='admin')
        response = self.client.get('/common/csv/')
        self.assertEqual(response.status_code, 200, "Non-staff user can get CSV files.")
        csv_items = json.loads(response.content.decode("utf-8"))['data']
        self.assertTrue(len(csv_items) > 0, "There is at least one CSV file available.")
        for app_name, app_data in csv_items.items():
            for csv_item in app_data.get('tables', []):
                self.assertEqual(set(csv_item.keys()), set(['url', 'name']), "Each CSV file for table has url and name.")
                response = self.client.get(csv_item['url'])
                self.assertTrue(response.status_code in [200, 204], 'The CSV file can be downloaded or is empty.')
            for csv_item in app_data.get('custom_exports', []):
                self.assertEqual(set(csv_item.keys()), set(['url', 'name']), "Each CSV file for custom export has url and name.")
                response = self.client.get(csv_item['url'])
                self.assertTrue(response.status_code in [200, 204], 'The CSV file can be downloaded or is empty.')

    def testLanguages(self):
        response = self.client.get('/common/languages/')
        self.assertDictEqual(json.loads(response.content.decode("utf-8"))['data'], settings.LANGUAGE_DOMAINS,
                             'API returns languages set in settings.py')
