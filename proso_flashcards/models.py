from django.conf import settings
from django.db import models
from proso_models.models import Item, Answer
from django.db.models.signals import pre_save
from django.dispatch import receiver


class Term(models.Model):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcard_terms")

    lang = models.CharField(max_length=2)
    name = models.TextField()

    def to_json(self, nested=False):
        json = {
            "id": self.pk,
            "item_id": self.item_id,
            "object_type": "fc_term",
            "lang": self.lang,
            "name": self.name,
        }
        if not nested:
            json["parents"] = [parent.to_json(nested=True) for parent in self.parents.all()]
        return json

    def __unicode__(self):
        return "{0.lang} - {0.name}".format(self)


class Context(models.Model):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcard_contexts")

    lang = models.CharField(max_length=2)
    name = models.TextField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)

    def to_json(self, nested=False):
        return {
            "id": self.pk,
            "item_id": self.item_id,
            "object_type": "fc_context",
            "lang": self.lang,
            "name": self.name,
            "content": self.content,
        }

    def __unicode__(self):
        return "{0.lang} - {0.name}".format(self)


class Flashcard(models.Model):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcards")

    lang = models.CharField(max_length=2)
    term = models.ForeignKey(Term, related_name="flashcards")
    context = models.ForeignKey(Context, related_name="flashcards")
    description = models.TextField(null=True)

    def to_json(self, nested=False):
        return {
            "id": self.pk,
            "item_id": self.item_id,
            "object_type": "fc_flashcard",
            "lang": self.lang,
            "term": self.term.to_json(),
            "context": self.context.to_json(),
            "description": self.description
        }

    def __unicode__(self):
        return "{0.term} - {0.context}".format(self)


class Category(models.Model):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcard_categories")

    lang = models.CharField(max_length=2)
    name = models.TextField()
    type = models.CharField(max_length=50, null=True, blank=True)
    subcategories = models.ManyToManyField("self", related_name="parents", symmetrical=False)
    terms = models.ManyToManyField(Term, related_name="parents")

    def to_json(self, nested=False):
        return {
            "id": self.pk,
            "item_id": self.item_id,
            "object_type": "fc_category",
            "lang": self.lang,
            "name": self.name,
            "type": self.type,
        }

    def __unicode__(self):
        return "{0.lang} - {0.name}".format(self)


class FlashcardAnswer(Answer):
    FROM_TERM = "t2d"
    FROM_DESCRIPTION = "d2t"
    DIRECTIONS = (
        (FROM_TERM, "From term to description"),
        (FROM_DESCRIPTION, "From description to term"),
    )

    direction = models.CharField(choices=DIRECTIONS, max_length=3)
    options = models.ManyToManyField(Term, related_name="answers_with_this_as_option")
    meta = models.TextField(null=True, blank=True)

    def to_json(self, nested=False):
        json = Answer.to_json(self)
        json['direction'] = self.direction
        json['meta'] = self.meta
        json['object_type'] = "fc_answer"
        if not nested:
            json["options"] = [term.to_json(nested=True) for term in self.options.all()]
        return json


@receiver(pre_save, sender=Term)
@receiver(pre_save, sender=Context)
@receiver(pre_save, sender=Flashcard)
@receiver(pre_save, sender=Category)
def create_items(sender, instance, **kwargs):
    if instance.item_id is None and instance.item is None:
        item = Item()
        item.save()
        instance.item = item


PROSO_MODELS_TO_EXPORT = [Category, Flashcard, FlashcardAnswer,
                          settings.PROSO_FLASHCARDS["term_extension"]
                          if "term_extension" in settings.PROSO_FLASHCARDS else Term,
                          settings.PROSO_FLASHCARDS["context_extension"]
                          if "context_extension" in settings.PROSO_FLASHCARDS else Context]
