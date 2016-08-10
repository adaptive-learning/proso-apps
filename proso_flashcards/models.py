from django.conf import settings
from django.db import models
from django.db.models import Q
from proso.django.models import ModelDiffMixin
from proso_models.models import Item, ItemRelation, Answer
from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from proso.django.models import disable_for_loaddata
import logging


LOGGER = logging.getLogger('django.request')


class TermManager(models.Manager):

    def prepare_related(self):
        return self


class Term(models.Model, ModelDiffMixin):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcard_terms")

    lang = models.CharField(max_length=2)
    name = models.TextField()

    objects = TermManager()

    def to_json(self, nested=False):
        return {
            "id": self.pk,
            "identifier": self.identifier,
            "item_id": self.item_id,
            "object_type": "fc_term",
            "lang": self.lang,
            "name": self.name,
        }

    def __str__(self):
        return "{0.lang} - {0.name}".format(self)


class ContextManager(models.Manager):

    def prepare_related(self):
        return self


class Context(models.Model, ModelDiffMixin):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcard_contexts")

    lang = models.CharField(max_length=2)
    name = models.TextField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)

    objects = ContextManager()

    def to_json(self, nested=False):
        json = {
            "id": self.pk,
            "identifier": self.identifier,
            "item_id": self.item_id,
            "object_type": "fc_context",
            "lang": self.lang,
            "name": self.name,
            "content": self.content,
            "active": self.active,
        }
        return json

    def __str__(self):
        return "{0.lang} - {0.name}".format(self)


class FlashcardManager(models.Manager):

    def prepare_related(self):
        return self.select_related(Flashcard.related_term(), Flashcard.related_context())

    def prepare(self):
        return self.select_related(Flashcard.related_term())


class Flashcard(models.Model, ModelDiffMixin):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcards")

    lang = models.CharField(max_length=2)
    term = models.ForeignKey(Term, related_name="flashcards")
    term_secondary = models.ForeignKey(Term, related_name="flashcards_as_secondary", null=True, blank=True, default=None)
    context = models.ForeignKey(Context, related_name="flashcards")
    description = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)
    additional_info = models.TextField(null=True, blank=True, default=None)

    objects = FlashcardManager()

    def to_json(self, nested=False, contexts=True):
        data = {
            "id": self.pk,
            "identifier": self.identifier,
            "item_id": self.item_id,
            "object_type": "fc_flashcard",
            "active": self.active,
            "lang": self.lang,
            "term": self.get_term().to_json(nested=True),
        }
        if hasattr(self, "options"):
            data["options"] = [o.to_json(nested=True) for o in sorted(self.options, key=lambda f: f.term.name)]
        if hasattr(self, 'practice_meta'):
            data['practice_meta'] = self.practice_meta
        if not nested and contexts:
            data["context"] = self.get_context().to_json(nested=True)
        else:
            data["context_id"] = self.context_id
        if self.term_secondary is not None:
            data["term_secondary"] = self.get_term_secondary().to_json(nested=True)
        if self.description is not None:
            data['description'] = self.description
        if self.additional_info is not None:
            data['additional_info'] = self.additional_info
        return data

    def get_term(self):
        extension = settings.PROSO_FLASHCARDS.get("term_extension", None)
        if extension is None:
            return self.term
        else:
            return getattr(self.term, extension.__name__.lower())

    def get_term_secondary(self):
        extension = settings.PROSO_FLASHCARDS.get("term_extension", None)
        if extension is None:
            return self.term_secondary
        else:
            return None if self.term_secondary is None else getattr(self.term_secondary, extension.__name__.lower())

    def get_context(self):
        extension = settings.PROSO_FLASHCARDS.get("context_extension", None)
        if extension is None:
            return self.context
        else:
            return getattr(self.context, extension.__name__.lower())

    @staticmethod
    def related_term():
        extension = settings.PROSO_FLASHCARDS.get("term_extension", None)
        if extension is None:
            return "term"
        else:
            return "term__{}".format(extension.__name__.lower())

    @staticmethod
    def related_term_secondary():
        extension = settings.PROSO_FLASHCARDS.get("term_extension", None)
        if extension is None:
            return "term_secondary"
        else:
            return "term_secondary__{}".format(extension.__name__.lower())

    @staticmethod
    def related_context():
        extension = settings.PROSO_FLASHCARDS.get("context_extension", None)
        if extension is None:
            return "context"
        else:
            return "context__{}".format(extension.__name__.lower())

    def __str__(self):
        return "{0.term} - {0.context}".format(self)


class Category(models.Model, ModelDiffMixin):
    class Meta:
        verbose_name_plural = "categories"

    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcard_categories")
    lang = models.CharField(max_length=2)
    name = models.TextField()
    type = models.CharField(max_length=50, null=True, blank=True)

    def to_json(self, nested=False):
        return {
            "id": self.pk,
            "identifier": self.identifier,
            "item_id": self.item_id,
            "object_type": "fc_category",
            "lang": self.lang,
            "name": self.name,
            "type": self.type,
        }

    def __str__(self):
        return "{0.lang} - {0.name}".format(self)


class FlashcardAnswerManager(models.Manager):

    def prepare_related(self):
        return self.prefetch_related('options__{}'.format(Flashcard.related_term()))

    def from_json(self, json_object, practice_context, practice_set, user_id, object_class=None):
        if object_class is None:
            object_class = FlashcardAnswer
        json_object = dict(json_object)
        flashcard_ids = set()
        flashcard_ids.add(json_object['flashcard_id'])
        if json_object.get('flashcard_answered_id') is not None:
            flashcard_ids.add(json_object['flashcard_answered_id'])
        if 'option_ids' in json_object:
            option_ids = set(json_object['option_ids'])
            if len(option_ids) < 1:
                raise Exception('If option_ids is given, it has to contain at least 1 items!')
            flashcard_ids |= option_ids
            if json_object['flashcard_id'] in option_ids:
                raise Exception('Option ids can not contain main flashcard id!')
            json_object['guess'] = 1.0 / (len(option_ids) + 1)
        else:
            json_object['guess'] = 0
        flashcards = {fc.id: fc for fc in Flashcard.objects.filter(pk__in=flashcard_ids)}
        if len(flashcard_ids) != len(flashcards):
            raise Exception("Invalid flashcard id (asked, answered or as option)")
        json_object['item_id'] = flashcards[json_object['flashcard_id']].item_id
        json_object['item_asked_id'] = flashcards[json_object['flashcard_id']].item_id
        json_object['item_answered_id'] = flashcards[json_object.get('flashcard_answered_id')].item_id if json_object.get('flashcard_answered_id') is not None else None
        json_object['lang'] = flashcards[json_object['flashcard_id']].lang
        answer = Answer.objects.from_json(json_object, practice_context, practice_set, user_id, object_class=object_class)
        if 'option_ids' in json_object:
            for option_id in set(json_object['option_ids']):
                answer.options.add(flashcards[option_id])
        answer.save()
        return answer


class FlashcardAnswer(Answer):
    FROM_TERM = "t2d"
    FROM_DESCRIPTION = "d2t"
    FROM_TERM_TO_TERM_SECONDARY = 't2ts'
    FROM_TERM_SECONDARY_TO_TERM = 'ts2t'

    options = models.ManyToManyField(Flashcard, related_name="answers_with_this_as_option")

    objects = FlashcardAnswerManager()

    def to_json(self, nested=False):
        json = Answer.to_json(self, nested=nested)
        json['object_type'] = "fc_answer"
        if not nested:
            json["options"] = [flashcard.to_json(nested=True) for flashcard in self.options.all()]
        return json


PROSO_MODELS_TO_EXPORT = [Category, Flashcard, FlashcardAnswer,
                          settings.PROSO_FLASHCARDS.get("context_extension", Context),
                          settings.PROSO_FLASHCARDS.get("term_extension", Term)]

PROSO_CUSTOM_EXPORT = {
    'answer': '''
        SELECT
            proso_models_answer.*
        FROM proso_models_answer
        INNER JOIN proso_flashcards_flashcardanswer
            ON proso_models_answer.id = answer_ptr_id
    ''',
    'context': '''
        SELECT
            proso_flashcards_context.id,
            proso_flashcards_flashcard.item_id AS item_id,
            proso_flashcards_term.name AS term_name,
            proso_flashcards_context.name AS context_name,
            proso_flashcards_flashcard.lang AS language
        FROM proso_flashcards_flashcard
        INNER JOIN proso_flashcards_term ON term_id = proso_flashcards_term.id
        INNER JOIN proso_flashcards_context ON context_id = proso_flashcards_context.id
        WHERE proso_flashcards_term.lang = proso_flashcards_context.lang
    '''
}


def _get_value_without_negation(value):
    if isinstance(value, int):
        return abs(value), value < 0
    else:
        if value is not None and value.startswith('-'):
            return value[1:], True
        else:
            return value, False


def _create_q(column, value):
    value, negation = _get_value_without_negation(value)
    q = Q(**{column: value})
    return ~q if negation else q


@receiver(pre_save, sender=Term)
@receiver(pre_save, sender=Context)
@receiver(pre_save, sender=Flashcard)
@receiver(pre_save, sender=Category)
@disable_for_loaddata
def create_items(sender, instance, **kwargs):
    """
    When one of the defined objects is created, initialize also its item.
    """
    if instance.item_id is None and instance.item is None:
        item = Item()
        if hasattr(instance, 'active'):
            item.active = getattr(instance, 'active')
        item.save()
        instance.item = item


@receiver(pre_save, sender=Term)
@receiver(pre_save, sender=Context)
@receiver(pre_save, sender=Flashcard)
@receiver(pre_save, sender=Category)
@disable_for_loaddata
def change_activity(sender, instance, **kwargs):
    if 'active' in instance.diff:
        instance.item.active = instance.active
        instance.item.save()


@receiver(post_save, sender=Flashcard)
@disable_for_loaddata
def add_parent(sender, instance, **kwargs):
    """
    When a flashcard is created, create also an item relation.
    """
    if not kwargs['created']:
        return
    for att in ['term', 'term_secondary', 'context']:
        if getattr(instance, att) is None:
            continue
        parent = getattr(instance, att).item_id
        child = instance.item_id
        ItemRelation.objects.get_or_create(
            parent_id=parent,
            child_id=child,
            visible=True,
            active=instance.active,
        )


@receiver(pre_save, sender=Flashcard)
@disable_for_loaddata
def change_parent(sender, instance, **kwargs):
    """
    When the given flashcard has changed. Look at term and context and change
    the corresponding item relation.
    """
    if instance.id is None:
        return
    if len({'term', 'term_id'} & set(instance.changed_fields)) != 0:
        diff = instance.diff
        parent = diff['term'][0] if 'term' in diff else diff['term_id'][0]
        parent_id = parent.item_id if isinstance(parent, Term) else Term.objects.get(pk=parent).item_id
        child_id = instance.item_id
        ItemRelation.objects.filter(parent_id=parent_id, child_id=child_id).delete()
        ItemRelation.objects.get_or_create(parent_id=instance.term.item_id, child_id=child_id, visible=True)
    if len({'term_secondary', 'term_secondary_id'} & set(instance.changed_fields)) != 0:
        diff = instance.diff
        child_id = instance.item_id
        parent = diff['term_secondary'][0] if 'term_secondary' in diff else diff['term_secondary_id'][0]
        if parent is not None:
            parent_id = parent.item_id if isinstance(parent, Term) else Term.objects.get(pk=parent).item_id
            ItemRelation.objects.filter(parent_id=parent_id, child_id=child_id).delete()
        if instance.term_secondary is not None or instance.term_secondary_id is not None:
            ItemRelation.objects.get_or_create(parent_id=instance.term_secondary.item_id, child_id=child_id, visible=True)
    if len({'context', 'context_id'} & set(instance.changed_fields)) != 0:
        diff = instance.diff
        parent = diff['context'][0] if 'context' in diff else diff['context_id'][0]
        parent_id = parent.item_id if isinstance(parent, Context) else Context.objects.get(pk=parent).item_id
        child_id = instance.item_id
        ItemRelation.objects.filter(parent_id=parent_id, child_id=child_id).delete()
        ItemRelation.objects.get_or_create(parent_id=instance.context.item_id, child_id=child_id, visible=True)


@receiver(pre_delete, sender=Flashcard)
@disable_for_loaddata
def delete_parent(sender, instance, **kwargs):
    """
    When the given flashcard is deleted, delete also the corresponding item
    relations.
    """
    ItemRelation.objects.filter(child_id=instance.item_id).delete()
