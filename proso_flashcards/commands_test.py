from django.core.management import call_command
from proso.django.test import TestCase
from proso_flashcards.models import Category, Context, Flashcard, Term
from proso_models.models import Item


class TestFlashcardsLoading(TestCase):

    CATEGORY_CHILDREN = {
        '0002': ['0003', '0004'],
        '0003': ['0005'],
    }

    CONTEXT_CHILDREN = {
        '0007': ['0002']
    }

    TERM_CHILDREN = {
        '0004': ['0002'],
        '0005': ['0003', '0004'],
    }

    FLASHCARD_CHILDREN = {
        "0006": ['0003', '0004'],
    }

    FLASHCARD_CHILDREN_CHANGED = {
        "0006": ['0002', '0004'],
    }

    @classmethod
    def setUpClass(cls):
        super(TestFlashcardsLoading, cls).setUpClass()
        call_command('find_item_types')

    def test_load_flashcards(self):
        call_command('load_flashcards', 'testproject/test_data/flashcards/categories.json')
        self._check_categories()
        call_command('load_flashcards', 'testproject/test_data/flashcards/contexts.json')
        self._check_contexts()
        call_command('load_flashcards', 'testproject/test_data/flashcards/terms.json')
        self._check_terms()
        call_command('load_flashcards', 'testproject/test_data/flashcards/flashcards.json')
        self._check_flashcards(self.FLASHCARD_CHILDREN)
        call_command('load_flashcards', 'testproject/test_data/flashcards/flashcards_changed.json')
        self._check_flashcards(self.FLASHCARD_CHILDREN_CHANGED)

    def _check_categories(self):
        categories = {c.item_id: c.identifier for c in Category.objects.filter(lang='en')}
        roots = list(categories.keys())
        for item, children in Item.objects.get_children_graph(roots).items():
            if item is None:
                continue
            children = set(children) & set(categories.keys())
            self.assertEqual(
                [categories[child] for child in children],
                self.CATEGORY_CHILDREN.get(categories[item], [])
            )

    def _check_contexts(self):
        categories = {c.item_id: c.identifier for c in Category.objects.filter(lang='en')}
        contexts = {c.item_id: c.identifier for c in Context.objects.filter(lang='en')}
        roots = list(categories.keys())
        for item, children in Item.objects.get_children_graph(roots).items():
            if item is None:
                continue
            children = set(children) & set(contexts.keys())
            self.assertEqual(
                [contexts[child] for child in children],
                self.CONTEXT_CHILDREN.get(categories[item], [])
            )

    def _check_terms(self):
        categories = {c.item_id: c.identifier for c in Category.objects.filter(lang='en')}
        terms = {t.item_id: t.identifier for t in Term.objects.filter(lang='en')}
        roots = list(categories.keys())
        for item, children in Item.objects.get_children_graph(roots).items():
            if item is None:
                continue
            children = set(children) & set(terms.keys())
            self.assertEqual(
                [terms[child] for child in children],
                self.TERM_CHILDREN.get(categories[item], [])
            )

    def _check_flashcards(self, flashcards_children):
        categories = {c.item_id: c.identifier for c in Category.objects.filter(lang='en')}
        contexts = {c.item_id: c.identifier for c in Context.objects.filter(lang='en')}
        terms = {t.item_id: t.identifier for t in Term.objects.filter(lang='en')}
        flashcards = {f.item_id: f for f in Flashcard.objects.select_related('term', 'context').filter(lang='en')}
        roots = list(categories.keys())
        for item, children in Item.objects.get_children_graph(roots).items():
            if item not in categories:
                continue
            children = set(children) & set(flashcards.keys())
            self.assertEqual(
                [flashcards[child].identifier for child in children],
                flashcards_children.get(categories[item], [])
            )

        parent_graph = Item.objects.get_parents_graph(list(flashcards.keys()))
        for flashcard in flashcards.values():
            parents = set(parent_graph[flashcard.item_id]) & (set(terms.keys()) | set(contexts.keys()))
            self.assertTrue(flashcard.term.item_id in parents)
            self.assertTrue(flashcard.context.item_id in parents)
            self.assertEqual(len(parents), 2)
