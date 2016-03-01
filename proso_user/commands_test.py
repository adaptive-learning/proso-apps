from django.core.management import call_command
from proso.django.test import TestCase
from proso_user.models import UserQuestion


class TeadQuestionsLoading(TestCase):

    def test_load_configab_experiments(self):
        self.maxDiff = None
        call_command('load_user_questions', 'testproject/test_data/user/user_questions.json')
        expected = {
            'active': True,
            'answer_type': 'c',
            'conditions': [{'object_type': 'user_question_condition', 'type': 'user_status', 'value': 'registered'}],
            'content': 'What is your sex?',
            'identifier': 'sex',
            'lang': 'en',
            'object_type': 'user_question',
            'on_events': [{'object_type': 'user_question_event', 'type': 'practice_sequence_finished', 'value': '5'}],
            'possible_answers': [
                {'content': 'Male', 'identifier': 'male', 'object_type': 'user_question_possible_answer'},
                {'content': 'Female', 'identifier': 'female', 'object_type': 'user_question_possible_answer'},
                {'content': 'Not specified', 'identifier': 'not_specified', 'object_type': 'user_question_possible_answer'}
            ],
            'repeat': False
        }
        self.assertEqual(self._remove_ids(UserQuestion.objects.filter(lang='en')[0].to_json()), expected)
