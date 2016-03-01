import django.test


class TestCase(django.test.TestCase):

    def setUp(self):
        self.client = django.test.Client()
        self.client.logout()

    def _remove_ids(self, value):
        if isinstance(value, dict):
            if 'id' in value:
                del value['id']
            return {k: self._remove_ids(v) for (k, v) in value.items()}
        elif isinstance(value, list):
            return [self._remove_ids(v) for v in value]
        else:
            return value
