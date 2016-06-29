from django.core.cache import cache
from functools import reduce
from proso.django.config import instantiate_from_config
from proso_flashcards.models import FlashcardAnswer, Category, Context, Flashcard
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
        opt_set_cache = cache.get('flashcard_construction__context_option_set', {})
        to_find = [fc for fc in flashcards if fc['item_id'] not in opt_set_cache]
        if len(to_find) > 0:
            context_ids = {flashcard['context']['id'] for flashcard in to_find}
            types_all_item_ids = set([c.item_id for c in Category.objects.filter(type='flashcard_type')])
            flashcard_item_ids = set([flashcard['item_id'] for flashcard in to_find])
            reachable_parents = Item.objects.get_reachable_parents(flashcard_item_ids, language=to_find[0]['lang'])
            flashcard_types = {item_id: set(reachable_parents.get(item_id, [])) & types_all_item_ids for item_id in flashcard_item_ids}

            context_item_ids = dict(Context.objects.filter(pk__in=context_ids).values_list('id', 'item_id'))

            secondary_terms = dict(Flashcard.objects.all().values_list('item_id', 'term_secondary_id'))
            found = {
                flashcard['item_id']: [i for i in reduce(
                    lambda xs, ys: set(xs) & set(ys),
                    Item.objects.get_leaves({context_item_ids[flashcard['context']['id']]} | flashcard_types[flashcard['item_id']], language=flashcard['lang']).values()
                ) if (secondary_terms.get(i) is not None) == ('term_secondary' in flashcard)]
                for flashcard in to_find
            }
            # trying to decrease probability of race condition
            opt_set_cache = cache.get('flashcard_construction__context_option_set', {})
            opt_set_cache.update(found)
            cache.set('flashcard_construction__context_option_set', opt_set_cache)
        return {fc['item_id']: opt_set_cache[fc['item_id']] for fc in flashcards}


class Direction(metaclass=abc.ABCMeta):
    def __init__(self, **kwargs):
        pass

    @abc.abstractmethod
    def get_direction(self, flashcard):
        pass


class RandomDirection(Direction):
    def get_direction(self, flashcard):
        if 'term_secondary' in flashcard:
            return random.choice([FlashcardAnswer.FROM_TERM_TO_TERM_SECONDARY, FlashcardAnswer.FROM_TERM_SECONDARY_TO_TERM])
        else:
            return random.choice([FlashcardAnswer.FROM_DESCRIPTION, FlashcardAnswer.FROM_TERM])


class OnlyFromTermDirection(Direction):
    def get_direction(self, flashcard):
        return FlashcardAnswer.FROM_TERM


class OnlyFromDescriptionDirection(Direction):
    def get_direction(self, flashcard):
        return FlashcardAnswer.FROM_DESCRIPTION
