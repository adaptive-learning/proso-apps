from django.conf import settings
from proso.django.test import TestCase
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
        self._categories = dict(map(lambda c: ((c.identifier, c.lang), c), Category.objects.all()))
        self._contexts = dict(map(lambda c: ((c.identifier, c.lang), c), Context.objects.all()))
        self._terms = dict(map(lambda t: ((t.identifier, t.lang), t), Term.objects.prefetch_related('parents').all()))
        self._flashcards = dict(map(lambda f: ((f.identifier, f.lang), f), Flashcard.objects.select_related('term', 'context').all()))

    def test_language(self):
        for lang in [None, 'cs', 'en', 'es']:
            if lang is not None:
                content = self._get_practice(language=lang)
            else:
                content = self._get_practice()
                lang = settings.LANGUAGE_CODE[:2]

            for flashcard in content['data']['flashcards']:
                self.assertEqual(flashcard['lang'], lang, 'The flashcard has an expected language.')
                self.assertEqual(flashcard['term']['lang'], lang, 'The term has an expected language.')
                self.assertEqual(flashcard['context']['lang'], lang, 'The context has an expected language.')
                for option in flashcard.get('options', []):
                    self.assertEqual(option['lang'], lang, 'The option flashcard has an expected language.')
                    self.assertEqual(option['term']['lang'], lang, 'The option term has an expected language.')

    def test_limit(self):
        for limit in [1, 5, 10]:
            content = self._get_practice(language='en', limit=limit)
            self.assertEqual(len(content['data']['flashcards']), limit, 'There is proper number of flashcards.')

    def test_without_contexts(self):
        content = self._get_practice(language='en', without_contexts=True)
        for flashcard in content['data']['flashcards']:
            self.assertIsNone(flashcard.get('context'), 'There is no context in flashcard object.')

    def test_types(self):
        for t in ['city', 'state']:
            content = self._get_practice(language='en', types='["%s"]' % t, limit=100)
            for flashcard in content['data']['flashcards']:
                self.assertEqual(flashcard['term']['type'], t, 'The term has an expected type.')
                for option in flashcard.get('options', []):
                    self.assertEqual(option['term']['type'], t, 'The option term has an expected type.')

    def test_contexts(self):
        for context in ['world', 'cz', 'africa']:
            filters = ['["%s"]' % context, '[%s]' % self._contexts[context, 'en'].id]
            for f in filters:
                content = self._get_practice(language='en', contexts=f, limit=100)
                for flashcard in content['data']['flashcards']:
                    self.assertEqual(flashcard['context']['identifier'], context, "The flashcard has an expected context.")
                    for option in flashcard.get('options', []):
                        self.assertEqual(self._flashcards[option['identifier'], 'en'].context.identifier, context, "The option flashcard has an expected context.")

    def test_categories(self):
        for category in ['world', 'cz', 'africa']:
            filters = ['["%s"]' % category, '[%s]' % self._categories[category, 'en'].id]
            for f in filters:
                content = self._get_practice(language='en', categories=f, limit=100)
                for flashcard in content['data']['flashcards']:
                    term_categories = map(lambda c: c.identifier, self._terms[flashcard['term']['identifier'], 'en'].parents.all())
                    self.assertTrue(category in term_categories, "The term has expected categories.")

    def test_avoid(self):
        avoid = map(lambda f: f.id, filter(lambda f: f.lang == 'en', self._flashcards.values()))[:10]
        content = self._get_practice(language='en', avoid=json.dumps(avoid), limit=100)
        found = map(lambda f: f['id'], content['data']['flashcards'])
        for a in avoid:
            self.assertFalse(a in found, "There is no flashcard with avoided id.")

    def test_deactivated_flashcards(self):
        content = self._get_practice(language='en', limit=100)
        found = map(lambda f: f['id'], content['data']['flashcards'])
        self.assertFalse(178 in found, "There is no flashcard which is not active.")

    def _get_practice(self, **kwargs):
        kwargs_str = '&'.join(map(lambda (key, val): '%s=%s' % (key, val), kwargs.items()))
        url = '/flashcards/practice/?%s' % kwargs_str
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, 'The status code is OK, url: %s' % url)
        content = json.loads(response.content)
        self.assertGreater(len(content['data']['flashcards']), 0, 'There is at least one flashcard, url: %s' % url)
        return content
