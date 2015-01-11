from django.db import models
from proso_models.models import Item, Answer
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from contextlib import closing
from django.db import connection
from proso_ab.models import Value
from django.utils.text import slugify
from proso_models.models import get_environment


class FlashcardManager(models.Manager):

    def reset(self, flashcards):
        categories_reset = {}
        for flashcard in flashcards:
            for category in flashcard.category_set.all():
                if category.id in categories_reset:
                    category_to_reset = categories_reset[category.id]
                else:
                    categories_reset[category.id] = category
                    category_to_reset = category
                category_to_reset.flashcards.remove(flashcard)
        for category in categories_reset.values():
            category.save()

    def from_identifier(self, identifier, language):
        try:
            flashcard = self.get(identifier=identifier, language=language)
        except Flashcard.DoesNotExist:
            flashcard = Flashcard(identifier=identifier, language=language)
        return flashcard


class Flashcard(models.Model):

    identifier = models.SlugField(null=True, blank=True, default=None)
    item = models.ForeignKey(Item, null=True, blank=True, default=None)
    language = models.CharField(max_length=50)
    reverse = models.TextField()
    obverse = models.TextField()
    type = models.CharField(max_length=50, null=True, blank=True, default=None)

    objects = FlashcardManager()

    class Meta:
        unique_together = (('item', 'language'), ('identifier', 'language'))

    def to_json(self, nested=False):
        result = {
            'id': self.pk,
            'item_id': self.item_id,
            'object_type': 'flashcard',
            'language': self.language,
            'reverse': self.reverse,
            'obverse': self.obverse,
            'identifier': self.identifier
        }
        if not nested:
            result['categories'] = map(lambda x: x.to_json(nested=True), self.category_set.all())
        return result


class CategoryManager(models.Manager):

    def from_identifier(self, identifier, language):
        try:
            category = self.get(identifier=identifier, language=language)
        except Category.DoesNotExist:
            category = Category(identifier=identifier, language=language)
        return category


class Category(models.Model):

    identifier = models.SlugField(null=True, blank=True, default=None)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, null=True, blank=True, default=None)
    language = models.CharField(max_length=50)
    flashcards = models.ManyToManyField(Flashcard)
    item = models.ForeignKey(Item, null=True, blank=True, default=None, related_name='flashcard_category_set')
    url_name = models.SlugField(unique=True)

    objects = CategoryManager()

    class Meta:
        unique_together = (('item', 'language'), ('identifier', 'language'))

    def to_json(self, nested=True):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'name': self.name,
            'url_name': self.url_name,
            'object_type': 'category',
            'language': self.language
        }


class DecoratedAnswer(models.Model):

    DIREACTION_REVERSE_ASKED = 1
    DIREACTION_OBVERSE_ASKED = 2

    DIRECTIONS = {
        DIREACTION_REVERSE_ASKED: 'reverse_asked',
        DIREACTION_OBVERSE_ASKED: 'obverse_asked'
    }

    general_answer = models.ForeignKey(Answer, blank=False, null=False, unique=True, related_name='flashcard_decoratedanswer_set')
    ip_address = models.CharField(max_length=39, null=True, blank=True, default=None)
    ab_values = models.ManyToManyField(Value, related_name='flashcard_decoratedanswer_set')
    language = models.CharField(max_length=50)
    direction = models.IntegerField(choices=DIRECTIONS.items())
    options = models.ManyToManyField(Item, related_name='flashcard_decoratedanswer_set')
    category = models.ForeignKey(Category, null=True, blank=True, default=None)

    def to_json(self, nested=False):
        return {
            'id': self.id,
            'object_type': 'answer',
            'item_asked_id': self.general_answer.item_asked_id,
            'item_answered_id': self.general_answer.item_answered_id,
            'ip_address': self.ip_address,
            'user_id': self.general_answer.user_id,
            'time': self.general_answer.time.strftime('%Y-%m-%d %H:%M:%S'),
            'response_time': self.general_answer.response_time,
            'language': self.language,
            'direction': self.DIRECTIONS[self.direction]
        }


@receiver(pre_save, sender=Flashcard)
@receiver(pre_save, sender=Category)
def add_item(sender, instance, **kwargs):
    if instance.item is None:
        item = Item()
        item.save()
        instance.item = item


@receiver(pre_save, sender=Category)
def add_url_name(sender, instance, **kwargs):
    instance.url_name = slugify(instance.language + '-' + instance.identifier)


@receiver(post_save, sender=Category)
def flashcard_parents(sender, **kwargs):
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
    for flashcard in category.flashcards.all():
        environment.write(
            'child',
            1,
            item=category.item_id,
            item_secondary=flashcard.item_id,
            symmetric=False)
        environment.write(
            'parent',
            1,
            item=flashcard.item_id,
            item_secondary=category.item_id,
            symmetric=False)


PROSO_MODELS_TO_EXPORT = [Category, DecoratedAnswer, Flashcard]
