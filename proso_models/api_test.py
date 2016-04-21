from django.conf import settings
from proso.django.test import TestCase
from proso_models.models import Item
from proso_flashcards.models import Term, Flashcard, Category, Context
import json


class PracticeAPITest(TestCase):

    fixtures = [
        'test_common_data.yaml',
        'test_models_data.yaml',
        'test_flashcards_data.yaml',
        'test_testapp_data.yaml'
    ]

    def setUp(self):
        self._categories = dict([((c.identifier, c.lang), c) for c in Category.objects.all()])
        self._contexts = dict([((c.identifier, c.lang), c) for c in Context.objects.all()])
        self._terms = dict([((t.identifier, t.lang), t) for t in Term.objects.all()])
        self._flashcards = dict([((f.identifier, f.lang), f) for f in Flashcard.objects.select_related('term', 'context').all()])

    def test_language(self):
        for lang in [None, 'cs', 'en']:
            if lang is not None:
                content = self._get_practice(language=lang)
            else:
                content = self._get_practice()
                lang = settings.LANGUAGE_CODE[:2]

            for question in content['data']:
                flashcard = question['payload']
                self.assertEqual(flashcard['lang'], lang, 'The flashcard has an expected language.')
                self.assertEqual(flashcard['term']['lang'], lang, 'The term has an expected language.')
                for option in flashcard.get('options', []):
                    self.assertEqual(option['lang'], lang, 'The option flashcard has an expected language.')
                    self.assertEqual(option['term']['lang'], lang, 'The option term has an expected language.')

    def test_limit(self):
        for limit in [1, 5, 10]:
            content = self._get_practice(language='en', limit=limit)
            self.assertEqual(len(content['data']), limit, 'There is proper number of questions.')

    def test_categories(self):
        for category_name, term_type_name in [('world', 'state'), ('cz', 'city'), ('africa', 'state')]:
            practice_filter = '[["category/{}"], ["category/{}"]]'.format(term_type_name, category_name)
            content = self._get_practice(language='en', filter=practice_filter, limit=100)
            for question in content['data']:
                term = self._terms[question['payload']['term']['identifier'], 'en']
                term_categories = Item.objects.get_parents_graph([term.item_id])[term.item_id]
                category = self._categories[category_name, 'en']
                term_type = self._categories[term_type_name, 'en']
                self.assertTrue({term_type.item_id, category.item_id}.issubset(term_categories), "The term has expected categories.")

    def test_avoid(self):
        avoid = list(map(lambda f: f.item_id, [f for f in list(self._flashcards.values()) if f.lang == 'en']))[:-10]
        content = self._get_practice(language='en', avoid=json.dumps(avoid), limit=10)
        found = [q['payload']['item_id'] for q in content['data']]
        self.assertEqual(set(found) & set(avoid), set(), "There is no flashcard with avoided id.")

    def _get_practice(self, **kwargs):
        kwargs_str = '&'.join(['%s=%s' % (key_val[0], key_val[1]) for key_val in list(kwargs.items())])
        url = '/models/practice/?%s' % kwargs_str
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, 'The status code is OK, url: %s' % url)
        content = json.loads(response.content.decode("utf-8"))
        self.assertGreater(len(content['data']), 0, 'There is at least one question, url: %s' % url)
        return content
