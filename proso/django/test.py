import django.test


class TestCase(django.test.TestCase):

    def setUp(self):
        self.client = django.test.Client()
        self.client.logout()



