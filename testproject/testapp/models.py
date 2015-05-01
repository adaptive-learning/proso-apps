from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from proso_flashcards.models import Term, Context, Flashcard
from proso.django.util import disable_for_loaddata


class ExtendedTerm(Term):
    extra_info = models.TextField()

    def to_json(self, nested=False):
        json = Term.to_json(self, nested)
        json["extra-info"] = self.extra_info
        return json

    @staticmethod
    def load_data(data, term):
        if 'extra-info' in data:
            term.extra_info = data["extra-info"]

    def dump_data(self, term):
        if self.extra_info:
            term["extra-info"] = self.extra_info


class ExtendedContext(Context):
    extra_info = models.TextField()

    def to_json(self, nested=False):
        json = Context.to_json(self, nested)
        json["extra-info"] = self.extra_info
        return json

    @staticmethod
    def load_data(data, context):
        if 'extra-info' in data:
            context.extra_info = data["extra-info"]

    def dump_data(self, context):
        if self.extra_info:
            context["extra-info"] = self.extra_info


settings.PROSO_FLASHCARDS["term_extension"] = ExtendedTerm
settings.PROSO_FLASHCARDS["context_extension"] = ExtendedContext


@receiver(pre_save, sender=ExtendedTerm)
@receiver(pre_save, sender=ExtendedContext)
@disable_for_loaddata
def create_items(sender, instance, **kwargs):
    pre_save.send(sender=sender.__bases__[0], instance=instance)
