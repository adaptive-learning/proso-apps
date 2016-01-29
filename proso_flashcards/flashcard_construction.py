from collections import defaultdict
import random
import abc
from proso_flashcards.models import Flashcard, FlashcardAnswer
from proso.django.config import instantiate_from_config


def get_option_set():
    return instantiate_from_config(
        'proso_flashcards', 'option_set',
        default_class='proso_flashcards.flashcard_construction.ContextOptionSet'
    )


def get_direction():
    return instantiate_from_config(
        'proso_flashcards', 'direction',
        default_class='proso_flashcards.flashcard_construction.RandomDirection'
    )


class OptionSet(metaclass=abc.ABCMeta):
    def __init__(self, **kwargs):
        pass

    @abc.abstractmethod
    def get_option_for_flashcards(self, flashcards):
        pass


class EmptyOptionSet(OptionSet):
    def get_option_for_flashcards(self, flashcards):
        return dict([(fc.item_id, []) for fc in flashcards])


class ContextOptionSet(OptionSet):
    def get_option_for_flashcards(self, flashcards):
        contexts = set()
        types = set()
        for flashcard in flashcards:
            contexts.add(flashcard.context_id)
            if flashcard.term.type is not None:
                types.add(flashcard.term.type)

        options_filter = {'context_id__in': contexts, 'active': True}
        if types:
            options_filter['term__type__in'] = types
        option_sets = defaultdict(set)
        for context, term_type, item in Flashcard.objects.filter(**options_filter).values_list("context", "term__type", "item_id"):
            option_sets[context, term_type].add(item)

        return dict([(fc.item_id, list(option_sets[fc.context_id, fc.term.type])) for fc in flashcards])


class Direction(metaclass=abc.ABCMeta):
    def __init__(self, **kwargs):
        pass

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
