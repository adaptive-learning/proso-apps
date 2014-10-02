from django.db import models
from proso_models.models import Item, Answer
from django.db.models.signals import pre_save
from django.dispatch import receiver
from contextlib import closing
from django.db import connection
from django.db.models import Count
from proso_ab.models import Value


class DecoratedAnswer(models.Model):

    general_answer = models.ForeignKey(Answer, blank=False, null=False, unique=True)
    ip_address = models.CharField(max_length=39, null=True, blank=True, default=None)
    ab_values = models.ManyToManyField(Value)

    def to_json(self, nested=False):
        return {
            'id': self.id,
            'object_type': 'answer',
            'question_item_id': self.general_answer.item_id,
            'item_asked_id': self.general_answer.item_asked_id,
            'item_answered_id': self.general_answer.item_answered_id,
            'ip_address': self.ip_address,
            'user_id': self.general_answer.user_id,
            'time': self.general_answer.time.strftime('%Y-%m-%d %H:%M:%S'),
            'response_time': self.general_answer.response_time
        }


class Resource(models.Model):

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

    def test(self, user_id, time):
        try:
            return list(Set.objects.
                    annotate(answers_num=Count('item__item_answers__id')).
                    order_by('answers_num', '?').
                    select_related('questions').
                    prefetch_related(
                        'questions__question_options',
                        'questions__question_options__option_images',
                        'questions__question_images', 'questions__resource__resource_images')[0].questions.all())
        except IndexError:
            return []

    def practice(self, recommendation, environment, user_id, time, n, questions=None):
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
        recommended = recommendation.recommend(environment, user_id, all_ids, time, n)
        if questions is not None:
            questions_dict = dict(zip(all_ids, questions))
        else:
            questions = (self.filter(item_id__in=recommended).
                    select_related('resource').
                    prefetch_related(
                        'question_options', 'question_options__option_images',
                        'question_images', 'resource__resource_images', 'set_set', 'category_set'
                    ))
            questions_dict = dict([(q.item_id, q) for q in questions])
        return map(lambda i: questions_dict[i], recommended)


class Question(models.Model):

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
            'resource': self.resource.to_json(nested=True) if self.resource else None
        }
        if not nested:
            result['sets'] = map(lambda s: s.to_json(nested=True), self.set_set.all())
            result['categories'] = map(lambda c: c.to_json(nested=True), self.category_set.all())
            result['options'] = map(lambda o: o.to_json(nested=True), self.question_options.all())
        return result


class CategoryManager(models.Manager):

    def from_name(self, name):
        try:
            category = self.get(name=name)
        except Category.DoesNotExist:
            category = Category(name=name)
            category.save()
        return category


class Category(models.Model):

    name = models.CharField(max_length=100, unique=True)
    questions = models.ManyToManyField(Question)
    item = models.ForeignKey(Item, null=True, blank=True, default=None, unique=True)

    objects = CategoryManager()

    def to_json(self, nested=False):
        result = {
            'object_type': 'category',
            'name': self.name,
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


class OptionManager(models.Manager):

    def get_correct_options(self, questions):
        opts = self.filter(question__in=questions, correct=True)
        opts_dict = dict([(opt.question_id, opt) for opt in opts])
        return map(lambda q: opts_dict.get(q.id, None), questions)

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


@receiver(pre_save, sender=Option)
@receiver(pre_save, sender=Resource)
@receiver(pre_save, sender=Set)
@receiver(pre_save, sender=Category)
@receiver(pre_save, sender=Question)
def sort_items(sender, instance, **kwargs):
    if instance.item is None:
        item = Item()
        item.save()
        instance.item = item
