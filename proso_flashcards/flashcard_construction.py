from collections import defaultdict
import random
import abc
from proso_flashcards.models import Flashcard, FlashcardAnswer
from proso.django.config import instantiate_from_subconfig


def get_option_set():
    return instantiate_from_subconfig(
        'proso_flashcards', 'option_set',
        default_class='proso_flashcards.flashcard_construction.ContextOptionSet'
    )


def get_direction():
    return instantiate_from_subconfig(
        'proso_flashcards', 'direction',
        default_class='proso_flashcards.flashcard_construction.RandomDirection'
    )


class OptionSet():
    def __init__(self, **kwargs):
        pass

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_option_for_flashcards(self, flashcards):
        pass


class EmptyOptionSet(OptionSet):
    def get_option_for_flashcards(self, flashcards):
        return dict(map(lambda fc: (fc.item_id, []), flashcards))


class ContextOptionSet(OptionSet):
    def get_option_for_flashcards(self, flashcards):
        contexts = set()
        for flashcard in flashcards:
            contexts.add(flashcard.context_id)

        option_sets = defaultdict(set)
        for context, item in Flashcard.objects.filter(context_id__in=contexts).values_list("context", "item_id"):
            option_sets[context].add(item)

        return dict(map(lambda fc: (fc.item_id, list(option_sets[fc.context_id])), flashcards))


class Direction():
    def __init__(self, **kwargs):
        pass

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_direction(self, flashcard):
        pass


class RandomDirection(Direction):
    def get_direction(self, flashcard):
        return random.choice([FlashcardAnswer.FROM_DESCRIPTION, FlashcardAnswer.FROM_TERM])


class OnlyFromTermDirection(Direction):
    def get_direction(self, flashcard):
        return FlashcardAnswer.FROM_TERM


class OnlyFromDescriptionDirection(Direction):
    def get_direction(self, flashcard):
        return FlashcardAnswer.FROM_DESCRIPTION
