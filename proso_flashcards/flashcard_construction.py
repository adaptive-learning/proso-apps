from functools import reduce
from proso.django.config import instantiate_from_config
from proso_flashcards.models import FlashcardAnswer, Category, Context
from proso_models.models import Item
import abc
import random


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
        return dict([(fc['item_id'], []) for fc in flashcards])


class ContextOptionSet(OptionSet):
    def get_option_for_flashcards(self, flashcards):
        context_ids = {flashcard['context']['id'] for flashcard in flashcards}
        types_all_item_ids = set([c.item_id for c in Category.objects.filter(type='flashcard_type')])
        flashcard_item_ids = set([flashcard['item_id'] for flashcard in flashcards])
        reachable_parents = Item.objects.get_reachable_parents(flashcard_item_ids)
        flashcard_types = {item_id: set(reachable_parents.get(item_id, [])) & types_all_item_ids for item_id in flashcard_item_ids}

        context_item_ids = dict(Context.objects.filter(pk__in=context_ids).values_list('id', 'item_id'))

        return {
            flashcard['item_id']: list(reduce(
                lambda xs, ys: set(xs) & set(ys),
                Item.objects.get_leaves({context_item_ids[flashcard['context']['id']]} | flashcard_types[flashcard['item_id']]).values()
            ))
            for flashcard in flashcards
        }


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
