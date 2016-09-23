import json
import random
from datetime import datetime

from django.conf import settings
from django.core.management import call_command
from proso.django.test import TestCase
from proso_concepts.models import Concept, Tag, Action


class LoadConceptsTest(TestCase):

    def test_load(self):
        call_command('load_concepts', 'testproject/test_data/concepts/concepts.json')
        self.assertEquals(Concept.objects.all().count(), 2 * 3, "All concepts are loaded.")
        self.assertSetEqual(set(Concept.objects.all().values_list("lang", flat=True).distinct()), {"en", "cs"}, "Concepts have correct languages.")
        self.assertEquals(Tag.objects.all().count(), 2 * 5, "All tags are created.")
        self.assertEquals(Action.objects.all().count(), 2 * 3 * 2, "All actions are created.")


class ConceptsAPITest(TestCase):

    fixtures = [
        'test_common_data.yaml',
        'test_models_data.yaml',
        'test_flashcards_data.yaml',
        'test_testapp_data.yaml',
        'test_concepts_data.yaml'
    ]

    def test_get_concepts(self):
        for lang in [None, 'cs', 'en']:
            content = self._get_concepts(lang=lang)
            self.assertEquals(len(content), 3, "API returns all concepts of requested language")
            if lang is None:
                lang = settings.LANGUAGE_CODE[:2]
            for concept in content:
                self.assertEquals(concept["lang"], lang, "API return concepts with correct language")

    def test_stats(self):
        concept = self._get_concepts()[0]
        concept2 = self._get_concepts()[1]
        flashcards = self._get_flashcards_in_concept(concept)
        flashcards2 = self._get_flashcards_in_concept(concept2)
        self.assertEquals(len(self._get_stats()), 0, "Return no stats for user without answer.")
        ids, corrects, time = [], 0, 0

        time_first = None
        for i in range(20):
            flashcard_id = flashcards[random.randint(0, len(flashcards) - 1)]["id"]
            flashcard2_id = flashcards2[random.randint(0, len(flashcards2) - 1)]["id"]
            correct = random.randint(0, 1)
            response_time = random.randint(300, 10000)
            ids.append(flashcard_id)
            corrects += correct
            time += response_time / 1000
            self._answer_flashcard(flashcard_id, correct, response_time)
            if time_first is None:
                time_first = datetime.today().timestamp()
            self._answer_flashcard(flashcard2_id, 1 - correct, response_time // 2)        # answer to different concept
            time_last = datetime.today().timestamp()
            stats = self._get_stats()[concept["identifier"]]
            self.assertEquals(stats["item_count"], len(flashcards), "Stats has correct 'item_count'")
            self.assertEquals(stats["practiced_items_count"], len(set(ids)), "Stats has correct 'practiced_items_count'")
            self.assertEquals(stats["answer_count"], len(ids), "Stats has correct 'answer_count'")
            self.assertEquals(stats["correct_answer_count"], corrects, "Stats has correct 'correct_answer_count'")
            self.assertAlmostEqual(stats["time_spent"], time, msg="Stats has correct 'time_spent'", delta=0.2)
            self.assertEquals(stats["session_count"], 1, "Stats has correct 'session_count'")
            self.assertAlmostEqual(stats["time_first"], time_first, msg="Stats has correct 'time_first'", delta=0.2)
            self.assertAlmostEqual(stats["time_last"], time_last, msg="Stats has correct 'time_last'", delta=0.2)

    def _get_concepts(self, lang=None):
        url = '/concepts/concepts?all=True'
        if lang is not None:
            url += "&language={}".format(lang)
        return json.loads(self.client.get(url).content.decode("utf-8"))["data"]

    def _get_flashcards_in_concept(self, concept):
        url = '/models/to_practice/?filter={}'.format(concept["query"])
        return json.loads(self.client.get(url).content.decode("utf-8"))["data"]

    def _answer_flashcard(self, flashcard_id, correct, response_time, direction="t2d"):
        url = '/models/practice/?limit=0'
        data = {"answer": {
            "answer_class": "flashcard_answer",
            "flashcard_id": flashcard_id,
            "flashcard_answered_id": flashcard_id if correct else None,
            "response_time": response_time,
            "question_type": direction,
        }}
        self.client.post(url, data=json.dumps(data), content_type="application/json")

    def _get_stats(self):
        url = '/concepts/user_stats'
        return json.loads(self.client.get(url).content.decode("utf-8"))["data"]
