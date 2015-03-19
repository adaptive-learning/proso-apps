from django.db import models
from proso_models.models import Item, Answer
from django.db.models.signals import pre_save
from django.dispatch import receiver


class Term(models.Model):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcard_terms")

    lang = models.CharField(max_length=2)
    name = models.TextField()

    def to_json(self):
        return {
            "id": self.pk,
            "item_id": self.item_id,
            "object_type": "term",
            "lang": self.lang,
            "name": self.name,
        }

    def __unicode__(self):
        return "{0.lang} - {0.text}".format(self)


class Context(models.Model):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcard_contexts")

    lang = models.CharField(max_length=2)
    name = models.TextField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)

    def to_json(self):
        return {
            "id": self.pk,
            "item_id": self.item_id,
            "object_type": "context",
            "lang": self.lang,
            "name": self.name,
            "content": self.content,
        }

    def __unicode__(self):
        return "{0.lang} - {0.text}".format(self)


class Flashcard(models.Model):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcards")

    lang = models.CharField(max_length=2)
    term = models.ForeignKey(Term, related_name="flashcards")
    context = models.ForeignKey(Context, related_name="flashcards")
    description = models.TextField(null=True)

    def to_json(self):
        return {
            "id": self.pk,
            "item_id": self.item_id,
            "object_type": "flashcard",
            "term": self.term.to_json(),
            "context": self.context.to_json(),
        }

    def __unicode__(self):
        return "{0.term} - {0.context}".format(self)


class Category(models.Model):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcard_categories")

    lang = models.CharField(max_length=2)
    name = models.TextField()
    type = models.CharField(max_length=50, null=True, blank=True)
    subcategories = models.ManyToManyField("self", related_name="parents")
    terms = models.ManyToManyField(Term, related_name="parents")

    def to_json(self):
        return {
            "id": self.pk,
            "item_id": self.item_id,
            "object_type": "term",
            "lang": self.lang,
            "name": self.name,
            "type": self.type,
        }

    def __unicode__(self):
        return "{0.lang} - {0.text}".format(self)


class FlashcardAnswer(Answer):
    from_term_direction = models.BooleanField()
    options = models.TextField(null=True)


@receiver(pre_save, sender=Term)
@receiver(pre_save, sender=Context)
@receiver(pre_save, sender=Flashcard)
@receiver(pre_save, sender=Category)
def create_items(sender, instance, **kwargs):
    if instance.item_id is None and instance.item is None:
        item = Item()
        item.save()
        instance.item = item
