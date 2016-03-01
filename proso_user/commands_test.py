from django.core.management import call_command
from django.test import TestCase
from proso_user.models import UserQuestion

class TeadQuestionsLoading(TestCase):

    def test_load_configab_experiments(self):
        call_command('load_user_questions', 'testproject/test_data/user/user_questions.json')
        expected = {
            'content': 'Jaké je tvé pohlaví?',
            'id': 1,
            'answer_type': 'c',
            'lang': 'cs',
            'active': True,
            'possible_answers': [
                {'content': 'Muž', 'object_type': 'user_question_possible_answer', 'id': 1, 'identifier': 'male'},
                {'content': 'Žena', 'object_type': 'user_question_possible_answer', 'id': 2, 'identifier': 'female'},
                {'content': 'Neuvedeno', 'object_type': 'user_question_possible_answer', 'id': 3, 'identifier': 'not_specified'}
            ],
            'on_events': [{'id': 1, 'object_type': 'user_question_event', 'type': 'practice_sequence_finished', 'value': '5'}],
            'identifier': 'sex',
            'object_type': 'user_question',
            'conditions': [{'id': 1, 'object_type': 'user_question_condition', 'type': 'user_status', 'value': 'registered'}],
            'repeat': False
        }
        self.assertEqual(UserQuestion.objects.all()[0].to_json(), expected)
