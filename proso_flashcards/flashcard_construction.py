from django.core.cache import cache
from functools import reduce
from proso_common.models import instantiate_from_config
from proso.list import flatten
from proso_flashcards.models import FlashcardAnswer, Category, Context, Flashcard
from proso_models.models import Item
import abc
import random
from proso.time import timeit


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
    def get_option_for_flashcards(self, flashcards_with_question_types):
        pass


class EmptyOptionSet(OptionSet):
    def get_option_for_flashcards(self, flashcards_with_question_types):
        return dict([(fc['item_id'], []) for fc, _ in flashcards_with_question_types])


class ContextOptionSet(OptionSet):
    @timeit(name='get_option_set')
    def get_option_for_flashcards(self, flashcards_with_question_types):
        question_types = {fc['id']: question_type for fc, question_type in flashcards_with_question_types}
        opt_set_cache = cache.get('flashcard_construction__context_option_set', {})
        to_find = [fc for (fc, question_type) in flashcards_with_question_types if (fc['item_id'], question_type) not in opt_set_cache]
        if len(to_find) > 0:
            context_ids = {self.get_context_id(flashcard) for flashcard in to_find}
            types_all_item_ids = set([c.item_id for c in Category.objects.filter(type='flashcard_type')])
            flashcard_item_ids = set([flashcard['item_id'] for flashcard in to_find])
            reachable_parents = Item.objects.get_reachable_parents(flashcard_item_ids, language=to_find[0]['lang'])
            flashcard_types = {item_id: set(reachable_parents.get(item_id, [])) & types_all_item_ids for item_id in flashcard_item_ids}

            context_item_ids = dict(Context.objects.filter(pk__in=context_ids).values_list('id', 'item_id'))

            secondary_terms = dict(Flashcard.objects.all().values_list('item_id', 'term_secondary_id'))
            found = {
                flashcard['item_id']: [i for i in reduce(
                    lambda xs, ys: set(xs) & set(ys),
                    Item.objects.get_leaves({context_item_ids[self.get_context_id(flashcard)]} | flashcard_types[flashcard['item_id']], language=flashcard['lang']).values()
                ) if (secondary_terms.get(i) is not None) == ('term_secondary' in flashcard)]
                for flashcard in to_find
            }
            if any(['term_secondary' in flashcard for flashcard in to_find]):
                # exclude options:
                #     1) with duplicate term/term_secondary
                #     2) with the same question but different answer
                translated = Item.objects.translate_item_ids(set(flatten(found.values())), language=to_find[0]['lang'])
                fc_dict = {flashcard['item_id']: flashcard for flashcard in to_find}
                found_translated = {
                    item_id: [translated[opt_id] for opt_id in options]
                    for item_id, options in found.items()
                }
                found = {}
                for fc_item_id, options in found_translated.items():
                    fc = fc_dict[fc_item_id]
                    if question_types[fc['id']] == FlashcardAnswer.FROM_TERM_TO_TERM_SECONDARY:
                        key_to = 'term_secondary'
                        key_from = 'term'
                    elif question_types[fc['id']] == FlashcardAnswer.FROM_TERM_SECONDARY_TO_TERM:
                        key_to = 'term'
                        key_from = 'term_secondary'
                    else:
                        found[fc['item_id']] = [opt['item_id'] for opt in options]
                        continue
                    options_by_keys = {}
                    for opt in sorted(options, key=lambda o: o['identifier']):
                        if self.get_context_id(fc) == opt['context_id'] and fc[key_from]['identifier'] == opt[key_from]['identifier']:
                            continue
                        options_by_keys[opt[key_to]['item_id']] = opt
                    if fc[key_to]['item_id'] in options_by_keys:
                        del options_by_keys[fc[key_to]['item_id']]
                    found[fc['item_id']] = [opt['item_id'] for opt in options_by_keys.values()]

            # trying to decrease probability of race condition
            opt_set_cache = cache.get('flashcard_construction__context_option_set', {})
            opt_set_cache.update(found)
            cache.set('flashcard_construction__context_option_set', opt_set_cache)
        return {fc['item_id']: opt_set_cache[fc['item_id']] for fc, _ in flashcards_with_question_types}

    def get_context_id(self, flashcard):
        if 'context' in flashcard:
            return flashcard['context']['id']
        else:
            return flashcard['context_id']


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
        if 'term_secondary' in flashcard:
            return FlashcardAnswer.FROM_TERM_TO_TERM_SECONDARY
        else:
            return FlashcardAnswer.FROM_TERM


class OnlyFromSecondaryTerm(Direction):
    def get_direction(self, flashcard):
        if 'term_secondary' not in flashcard:
            raise Exception('There is no secondary term, so the question type "from secondary term" is not valid.')
        return FlashcardAnswer.FROM_TERM_SECONDARY_TO_TERM


class OnlyFromDescriptionDirection(Direction):
    def get_direction(self, flashcard):
        if 'term_secondary' in flashcard:
            raise Exception('There is a secondary term, so the question type "from description" is not valid.')
        return FlashcardAnswer.FROM_DESCRIPTION
