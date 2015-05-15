from django.contrib.auth.models import User
from proso.django.config import reset_overridden
from proso.django.test import TestCase
import json


class CommonAPITest(TestCase):

    @classmethod
    def setUpClass(cls):
        User.objects.create_superuser('admin', 'admin@test.com', 'admin')

    def tearDown(self):
        self.client.logout()
        reset_overridden()

    def testConfig(self):
        response = self.client.get('/common/config/?config.my.super.property=true')
        self.assertEqual(response.status_code, 200, 'The configuration is available.')
        self.assertFalse('my' in json.loads(response.content)['data'], "Non-staff user can't override configuration properties.")
        self.client.login(username='admin', password='admin')
        response = self.client.get('/common/config/?config.my.super.property=true')
        self.assertEqual(response.status_code, 200, 'The configuration is available.')
        self.assertEqual(
            json.loads(response.content)['data']['my']['super']['property'],
            True,
            'Staff user can override configuration properties'
        )

    def testAnalysis(self):
        response = self.client.get('/common/csv/')
        self.assertEqual(response.status_code, 401, "Non-staff user can't get CSV files.")
        self.client.login(username='admin', password='admin')
        response = self.client.get('/common/csv/')
        self.assertEqual(response.status_code, 200, "Non-staff user can get CSV files.")
        csv_items = json.loads(response.content)['data']
        self.assertTrue(len(csv_items) > 0, "There is at least one CSV file available.")
        for csv_item in csv_items:
            self.assertEqual(set(csv_item.keys()), set(['url', 'table']), "Each CSV file has url and table name.")
