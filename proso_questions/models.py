from django.db import models
from proso_models.models import Item, Answer
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from contextlib import closing
from django.db import connection
from django.db.models import Count
from django.utils.text import slugify
from proso_models.models import get_environment
from collections import defaultdict
import abc
from proso.django.config import instantiate_from_config
from proso.django.util import disable_for_loaddata


def get_test_evaluator():
    return instantiate_from_config(
        'proso_questions', 'test_evaluator',
        default_class='proso_questions.models.SimpleTestEvaluator'
    )


class ResourceManager(models.Manager):

    def reset(self, resource):
        for image in resource.resource_images.all():
            image.delete()

    def from_identifier(self, identifier, reset=False):
        try:
            resource = self.get(identifier=identifier)
            if reset:
                self.reset(resource)
        except Resource.DoesNotExist:
            resource = Resource(identifier=identifier)
        return resource


class Resource(models.Model):

    identifier = models.SlugField(unique=True, null=True, blank=True, default=None)
    text = models.TextField()
    item = models.ForeignKey(Item, null=True, blank=True, default=None, unique=True)

    def to_json(self, nested=False):
        return {
            'object_type': 'resource',
            'id': self.id,
            'item_id': self.item_id,
            'text': self.text,
            'images': map(lambda i: i.to_json(nested=True), list(self.resource_images.all()))
        }


class QuestionManager(models.Manager):

    def reset(self, questions):
        categories_to_reset = {}
        sets_to_reset = {}
        for question in questions:
            for category in question.category_set.all():
                if category.id in categories_to_reset:
                    category_to_reset = categories_to_reset[category.id]
                else:
                    categories_to_reset[category.id] = category
                    category_to_reset = category
                category.questions.remove(question)
            for question_set in question.set_set.all():
                if question_set.id in sets_to_reset:
                    set_to_reset = sets_to_reset[question_set.id]
                else:
                    sets_to_reset[question_set.id] = question_set
                    set_to_reset = question_set
                set_to_reset.questions.remove(question)
            for image in question.question_images.all():
                image.delete()
        for category_to_reset in categories_to_reset.itervalues():
            category_to_reset.save()
        for set_to_reset in sets_to_reset.itervalues():
            set_to_reset.save()

    def from_identifiers(self, identifiers, reset=False):
        if reset:
            objects = self.prefetch_related('category_set', 'set_set', 'question_images')
        else:
            objects = self
        questions = objects.filter(identifier__in=identifiers)
        if reset:
            self.reset(questions)
        result = defaultdict(Question)
        for q in questions:
            result[q.identifier] = q
        return result

    def test(self, user_id, time):
        try:
            return (Set.objects.
                    annotate(answers_num=Count('item__item_answers__id')).
                    order_by('answers_num', '?').
                    select_related('questions').
                    prefetch_related(
                        'questions__question_options',
                        'questions__question_options__option_images',
                        'questions__question_images', 'questions__resource__resource_images')[0])
        except IndexError:
            return []

    def practice(self, item_selector, environment, user_id, time, n, questions=None):
        if questions is not None:
            all_ids = map(lambda x: x.item_id, questions)
        else:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    """
                    SELECT item_id
                    FROM proso_questions_question
                    ORDER BY RANDOM()
                    LIMIT %s
                    """, [n * 100])
                all_ids = map(lambda x: x[0], cursor.fetchall())
        n = min(n, len(all_ids))
        selected_items = item_selector.select(environment, user_id, all_ids, time, n)
        if questions is not None:
            questions_dict = dict(zip(all_ids, questions))
        else:
            questions = (self.filter(item_id__in=selected_items).
                    select_related('resource').
                    prefetch_related(
                        'question_options', 'question_options__option_images',
                        'question_images', 'resource__resource_images', 'set_set', 'category_set'))
            questions_dict = dict([(q.item_id, q) for q in questions])
        return map(lambda i: questions_dict[i], selected_items)


class Question(models.Model):

    identifier = models.SlugField(unique=True, null=True, blank=True, default=None)
    text = models.TextField()
    resource = models.ForeignKey(
        Resource, null=True, blank=True, default=None, related_name='resource_questions')
    item = models.ForeignKey(Item, null=True, blank=True, default=None, unique=True)

    objects = QuestionManager()

    def to_json(self, nested=False):
        result = {
            'id': self.pk,
            'item_id': self.item_id,
            'text': self.text,
            'object_type': 'question',
            'images': map(lambda i: i.to_json(nested=True), self.question_images.all()),
            'resource': self.resource.to_json(nested=True) if self.resource else None,
            'identifier': self.identifier
        }
        if not nested:
            result['sets'] = map(lambda s: s.to_json(nested=True), self.set_set.all())
            result['categories'] = map(lambda c: c.to_json(nested=True), self.category_set.all())
            result['options'] = sorted(map(lambda o: o.to_json(nested=True), self.question_options.all()), key=lambda opt: opt.get('order', 0))
        return result

    def __unicode__(self):
        return u'Question: {0}'.format(self.text[:100])


class CategoryManager(models.Manager):

    def from_name(self, name):
        try:
            category = self.get(name=name)
        except Category.DoesNotExist:
            category = Category(name=name, url_name=slugify(name))
            category.save()
        return category


class Category(models.Model):

    name = models.CharField(max_length=100, unique=True)
    questions = models.ManyToManyField(Question)
    item = models.ForeignKey(Item, null=True, blank=True, default=None, unique=True)
    url_name = models.SlugField(unique=True)

    objects = CategoryManager()

    def to_json(self, nested=False):
        result = {
            'object_type': 'category',
            'name': self.name,
            'url_name': self.url_name,
            'id': self.id,
            'item_id': self.item_id
        }
        return result


class SetManager(models.Manager):

    def from_name(self, name):
        try:
            question_set = self.get(name=name)
        except Set.DoesNotExist:
            question_set = Set(name=name)
            question_set.save()
        return question_set


class Set(models.Model):

    name = models.CharField(max_length=100, unique=True)
    questions = models.ManyToManyField(Question)
    item = models.ForeignKey(Item, null=True, blank=True, default=None, unique=True)

    objects = SetManager()

    def to_json(self, nested=False):
        return {
            'name': self.name,
            'object_type': 'set',
            'id': self.id,
            'item_id': self.item_id,
        }


class DecoratedAnswer(models.Model):

    general_answer = models.ForeignKey(Answer, blank=False, null=False, unique=True)
    from_test = models.ForeignKey(Set, null=True, blank=True, default=None)

    def to_json(self, nested=False):
        json = Answer.to_json(self.general_answer)
        json['id'] = self.pk
        json['from_test'] = self.from_test.to_json(nested=True) if self.from_test else None
        return json


class OptionManager(models.Manager):

    def reset(self, option):
        for image in option.option_images.all():
            image.delete()

    def from_question(self, question, reset=False):
        options = list(question.question_options.all())
        if reset:
            for option in options:
                self.reset(option)
        return options

    def get_correct_options(self, questions):
        opts = self.filter(question__in=questions, correct=True)
        opts_dict = dict([(opt.question_id, opt) for opt in opts])
        return map(lambda q: opts_dict.get(q.id if isinstance(q, Question) else int(q), None), questions)

    def get_correct_option(self, question):
        return self.get(question=question, correct=True)


class Option(models.Model):

    text = models.TextField()
    question = models.ForeignKey(Question, null=False, blank=False, related_name='question_options')
    order = models.IntegerField(null=True, blank=True, default=None)
    correct = models.BooleanField(default=False)
    item = models.ForeignKey(Item, null=True, blank=False, default=None, unique=True)

    objects = OptionManager()

    def to_json(self, nested=False):
        return {
            'text': self.text,
            'order': self.order,
            'correct': self.correct,
            'question': self.question_id if nested else self.question.to_json(nested=True),
            'id': self.pk,
            'item_id': self.item_id,
            'object_type': 'option',
            'images': map(lambda i: i.to_json(nested=True), self.option_images.all())
        }


class Image(models.Model):

    file = models.ImageField(upload_to='image/', max_length=255)
    name = models.CharField(max_length=50)
    resource = models.ForeignKey(Resource, null=True, blank=True, default=None, related_name='resource_images')
    question = models.ForeignKey(Question, null=True, blank=True, default=None, related_name='question_images')
    option = models.ForeignKey(Option, null=True, blank=True, default=None, related_name='option_images')

    def __str__(self):
        return str(self.to_json())

    def to_json(self, nested=False):
        return {'name': self.name, 'url': self.file.url}


class TestEvaluator:

    @abc.abstractmethod
    def evaluate(self, answers):
        """
        Args:
            answers ([proso_models.model.Answer]):
                user's answers
        Return:
            [(proso_models.model.Answer, int)]:
                score earned by each answer
        """
        pass

    @abc.abstractmethod
    def score_to_pass(self):
        pass

    @abc.abstractmethod
    def score_max(self):
        pass


class SimpleTestEvaluator(TestEvaluator):

    def __init__(self, score_to_pass=0, score_max=0, score_correct=1, score_wrong=0, score_not_answered=0):
        self._score_to_pass = score_to_pass
        self._score_max = score_max
        self._score_correct = score_correct
        self._score_wrong = score_wrong
        self._score_not_answered = score_not_answered

    def evaluate(self, answers):
        result = []
        for answer in answers:
            score = 0
            if answer.general_answer.item_answered_id is None:
                score = self._score_not_answered
            elif answer.general_answer.item_answered_id == answer.general_answer.item_asked_id:
                score = self._score_correct
            else:
                score = self._score_wrong
            result.append((answer, score))
        return result

    def score_to_pass(self):
        return self._score_to_pass

    def score_max(self):
        return self._score_max


class CategoryTestEvaluator(TestEvaluator):

    def __init__(self, score_by_categories, score_to_pass):
        """
        category name:
            'correct': score,
            'unknown': score,
            'wrong': score,
            'answers': expected number of answers
        """
        self._score_by_categories = score_by_categories
        self._score_to_pass = score_to_pass

    def evaluate(self, answers):
        q_item_ids = map(lambda a: a.general_answer.item_id, answers)
        questions = dict(map(lambda q: (q.item_id, q), list(Question.objects.prefetch_related('category_set').filter(item_id__in=q_item_ids))))
        result = []
        found_answers = {}
        for answer in answers:
            question = questions[answer.general_answer.item_id]
            [category] = list(question.category_set.all())
            score_rule = self._score_by_categories[category.name]
            score = 0
            if answer.general_answer.item_answered_id is None:
                score = score_rule.get('unknown', 0)
            elif answer.general_answer.item_answered_id == answer.general_answer.item_asked_id:
                score = score_rule.get('correct', 0)
            else:
                score = score_rule.get('wrong', 0)
            found_answers[category.name] = found_answers.get(category.name, 0) + 1
            result.append((answer, score))
        for category_name, number_of_answers in found_answers.iteritems():
            if number_of_answers != self._score_by_categories[category_name]['answers']:
                raise Exception('The test expects %s answers in category "%s", found %s.' % (
                    self._score_by_categories[category_name]['answers'],
                    category_name,
                    number_of_answers))
        return result

    def score_to_pass(self):
        return self._score_to_pass

    def score_max(self):
        score_sum = 0
        for i in self._score_by_categories:
            val = self._score_by_categories[i]
            score_sum += val['correct'] * val['answers']
        return score_sum


@receiver(pre_save, sender=Option)
@receiver(pre_save, sender=Resource)
@receiver(pre_save, sender=Set)
@receiver(pre_save, sender=Category)
@receiver(pre_save, sender=Question)
@disable_for_loaddata
def sort_items(sender, instance, **kwargs):
    if instance.item_id is None and instance.item is None:
        item = Item()
        item.save()
        instance.item = item


@receiver(post_save, sender=Category)
@disable_for_loaddata
def question_parents(sender, **kwargs):
    environment = get_environment()
    category = kwargs['instance']
    # FIXME: temporary fix, remove once the environment has the delete()
    # method.
    with closing(connection.cursor()) as cursor:
        cursor.execute(
            """
            DELETE FROM proso_models_variable
            WHERE
                (key = 'parent' AND item_secondary_id = %s)
                OR
                (key = 'child' AND item_primary_id = %s)
            """, [category.item_id, category.item_id])
        cursor.execute(
            """
            DELETE FROM proso_models_audit
            WHERE
                (key = 'parent' AND item_secondary_id = %s)
                OR
                (key = 'child' AND item_primary_id = %s)
            """, [category.item_id, category.item_id])
    for question in category.questions.all():
        environment.write(
            'child',
            1,
            item=category.item_id,
            item_secondary=question.item_id,
            symmetric=False,
            permanent=True)
        environment.write(
            'parent',
            1,
            item=question.item_id,
            item_secondary=category.item_id,
            symmetric=False,
            permanent=True)


@receiver(post_delete, sender=Image)
@disable_for_loaddata
def image_delete(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(False)


PROSO_MODELS_TO_EXPORT = [Category, DecoratedAnswer, Option, Question, Resource, Set]
