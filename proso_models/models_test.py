from django.contrib.auth.models import User
from .models import DatabaseEnvironment
from .models import Item
import django.test as test
from django.conf import settings
import proso.models.environment as environment


class ItemManagerTest(test.TestCase):

    '''
        1
       / \
      2   3   4
     / \ / \ /
    5   6   7
    '''
    GRAPH = {
        1: [2, 3],
        2: [5, 6],
        3: [6, 7],
        4: [7],
        5: [],
        6: [],
        7: [],
    }

    @classmethod
    def setUpClass(cls):
        super(ItemManagerGraphTest, cls).setUpClass()
        for item_id in ItemManagerGraphTest.GRAPH.keys():
            item = Item.objects.create(id=item_id)
        for item_id, children in ItemManagerGraphTest.GRAPH.items():
            item = Item.objects.get(id=item_id)
            for child in children:
                ItemRelation.objects.create(parent=item, child=Item.objects.get(id=child))
            item.save()

    def test_parents_graph(self):
        self.assertEqual(Item.objects.get_parents_graph([4]), {None: [4]})
        self.assertEqual(
            Item.objects.get_parents_graph([6]),
            {None: [6], 6: [2, 3], 2: [1], 3: [1]}
        )
        self.assertEqual(
            Item.objects.get_parents_graph([6, 7]),
            {None: [6, 7], 6: [2, 3], 7: [3, 4], 2: [1], 3: [1]}
        )

    def test_children_graph(self):
        self.assertEqual(Item.objects.get_children_graph([7]), {None: [7]})
        self.assertEqual(
            Item.objects.get_children_graph([1]),
            {None: [1], 1: [2, 3], 2: [5, 6], 3: [6, 7]}
        )
        self.assertEqual(
            Item.objects.get_children_graph([2, 4]),
            {None: [2, 4], 2: [5, 6], 4: [7]}
        )

    def test_get_leaves(self):
        self.assertEqual(Item.objects.get_leaves([4]), {7})
        self.assertEqual(Item.objects.get_leaves([2, 3]), {5, 6, 7})


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
