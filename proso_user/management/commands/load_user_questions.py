from django.core.management.base import BaseCommand
from django.db import transaction
from jsonschema import validate
from proso_user.models import UserQuestion, UserQuestionPossibleAnswer, UserQuestionEvent, UserQuestionCondition
import json
import os
import re


class Command(BaseCommand):
    help = "Load questions for users from JSON file"

    ANSWER_TYPES = {
        'open': UserQuestion.TYPE_OPEN,
        'closed': UserQuestion.TYPE_CLOSED,
        'mixed': UserQuestion.TYPE_MIXED,
    }

    def add_arguments(self, parser):
        parser.add_argument('filename')

    def handle(self, *args, **options):
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "user_questions_schema.json"), "r", encoding='utf8') as schema_file:
            schema = json.load(schema_file)
        with open(options['filename'], 'r', encoding='utf8') as json_file:
            with transaction.atomic():
                data = json.load(json_file)
                validate(data, schema)
                self._load_questions(data['questions'])

    def _load_questions(self, questions_json):
        print("\nLoading categories")
        for question_json in questions_json:
            langs = [k[-2:] for k in list(question_json.keys()) if re.match(r'^content-\w\w$', k)]
            for lang in langs:
                question = UserQuestion.objects.filter(identifier=question_json['id'], lang=lang).first()
                if question is None:
                    question = UserQuestion(identifier=question_json['id'], lang=lang)
                question.content = question_json['content-{}'.format(lang)]
                question.closed = question_json.get('answer-type', 'o')
                question.active = question_json.get('active', True)
                question.repeat = question_json.get('repeat', False)
                question.answer_type = self.ANSWER_TYPES[question_json.get('answer-type', 'mixed')]
                if question.pk is not None:
                    possible_answer_ids = [a['id'] for a in question_json['possible-answers']]
                    for answer in question.possible_answers.all():
                        if answer.identifier not in possible_answer_ids:
                            answer.active = False
                            answer.save()
                question.save()
                question.on_events.clear()
                for event_json in question_json.get('events', []):
                    event = UserQuestionEvent.objects.from_type_value(event_json['type'], event_json['value'])
                    question.on_events.add(event)
                question.conditions.clear()
                for condition_json in question_json.get('conditions', []):
                    condition = UserQuestionCondition.objects.from_type_value(condition_json['type'], condition_json['value'])
                    question.conditions.add(condition)
                question.save()
                for possible_answer_json in question_json.get('possible-answers', []):
                    possible_answer = UserQuestionPossibleAnswer.objects.filter(
                        identifier=possible_answer_json['id'],
                        question=question).first()
                    if possible_answer is None:
                        possible_answer = UserQuestionPossibleAnswer(
                            identifier=possible_answer_json['id'],
                            question=question)
                    possible_answer.active = possible_answer_json.get('active', True)
                    possible_answer.content = possible_answer_json['content-{}'.format(lang)]
                    possible_answer.save()
