import abc
import random
import math
import logging
import proso.django.log
import numpy
import json
from collections import defaultdict

LOGGER = logging.getLogger('django.request')

DEFAULT_TARGET_PROBABILITY = 0.65


class ItemSelection(metaclass=abc.ABCMeta):
    def __init__(self, predictive_model, target_probability=DEFAULT_TARGET_PROBABILITY, history_adjustment=True):
        self._predictive_model = predictive_model
        self._target_probability = target_probability
        self._predictions_cache = None
        self._rolling_success = None
        self._history_adjustment = history_adjustment

    @abc.abstractmethod
    def select(self, environment, user, items, time, practice_context, n, **kwargs):
        """
        Returns a list of items chosen to practice and a list of JSONs (or
        Nones) providing meta info about the selection.
        """
        pass

    def get_predictions(self, environment, user=None, items=None, time=None):
        if self._predictions_cache is None:
            if user is None:
                raise Exception('Can not compute predictions without user.')
            if items is None:
                raise Exception('Can not compute predictions without items.')
            if time is None:
                raise Exception('Can not compute predictions without time.')
            self._predictions_cache = dict(
                zip(items, self._predictive_model.predict_more_items(environment, user, items, time)))
        return self._predictions_cache

    def history_adjustment(self):
        return self._history_adjustment

    def get_target_probability(self, environment, user, practice_context=None):
        if self._history_adjustment:
            return adjust_target_probability(self._target_probability,
                                             self.get_rolling_success(environment, user, practice_context))
        else:
            return self._target_probability

    def get_rolling_success(self, environment, user, practice_context=None):
        if self._rolling_success is None:
            self._rolling_success = environment.rolling_success(user=user, context=practice_context)
        return self._rolling_success


class RandomItemSelection(ItemSelection):
    def select(self, environment, user, items, time, practice_context, n, **kwargs):
        candidates = random.sample(items, min(n, len(items)))
        # HACK: option selector needs predictions already prepared
        self.get_predictions(environment, user, items, time)
        return candidates, [None for _ in candidates]

    def __str__(self):
        return 'RANDOM ITEM SELECTION'


class TestWrapperItemSelection(ItemSelection):
    def __init__(self, item_selector, nth=10):
        self._item_selector = item_selector
        self._nth = nth

    def select(self, environment, user, items, time, practice_context, n, **kwargs):
        if self._nth < n:
            raise Exception(
                'Number of items ({}) to select has to be lower than or equal to the "nth" ({}) parameter.'.format(n,
                                                                                                                   self._nth))
        items_in_queue = kwargs.get('items_in_queue', 0)
        number_of_answers = environment.number_of_answers(user=user, context=practice_context) + items_in_queue
        test_position = number_of_answers % self._nth
        if test_position != 0:
            test_position = self._nth - test_position
        if test_position >= n:
            return self._item_selector.select(environment, user, items, time, practice_context, n, **kwargs)
        LOGGER.debug(
            'Providing random test item on position {}, items in queue {}'.format(test_position, items_in_queue))
        # HACK: option selector needs predictions already prepared
        self.get_predictions(environment, user, items, time)
        test_item = random.choice(items)
        test_meta = {'test': 'random_without_options'}
        items = [i for i in items if i != test_item]
        selected_items, meta = self._item_selector.select(environment, user, items, time, practice_context, n - 1,
                                                          **kwargs) if n - 1 > 0 else ([], [])
        return selected_items[:test_position] + [test_item] + selected_items[test_position:], meta[:test_position] + [
            test_meta] + meta[test_position:]

    def history_adjustment(self):
        return self._item_selector.history_adjustment()

    def get_predictions(self, environment, user=None, items=None, time=None):
        return self._item_selector.get_predictions(environment, user=user, items=items, time=time)

    def get_target_probability(self, environment, user, practice_context=None):
        return self._item_selector.get_target_probability(environment, user, practice_context=practice_context)

    def get_rolling_success(self, environment, user, practice_context=None):
        return self._item_selector.get_rolling_success(environment, user, practice_context=practice_context)


class ScoreItemSelection(ItemSelection):
    def __init__(
            self, predictive_model, weight_probability=10.0, weight_number_of_answers=5.0,
            weight_time_ago=5, weight_parent_time_ago=5.0, weight_parent_number_of_answers=2.5,
            target_probability=DEFAULT_TARGET_PROBABILITY, time_ago_max=120, recompute_parent_score=True,
            history_adjustment=True, estimate_parent_factors=True):
        ItemSelection.__init__(self, predictive_model, target_probability, history_adjustment)
        self._weight_probability = weight_probability
        self._weight_number_of_answers = weight_number_of_answers
        self._weight_time_ago = weight_time_ago
        self._weight_parent_time_ago = weight_parent_time_ago
        self._weight_parent_number_of_answers = weight_parent_number_of_answers
        self._estimate_parent_factors = estimate_parent_factors
        self._recompute_parent_score = recompute_parent_score
        self._time_ago_max = time_ago_max

    def select(self, environment, user, items, time, practice_context, n, **kwargs):
        parents = environment.get_items_with_values_more_items('parent', items=items)
        if self._estimate_parent_factors:
            related_items = items
        else:
            parent_ids = set(sum([[p for p, v in ps] for ps in list(parents.values())], []))
            children = environment.get_items_with_values_more_items('child', items=parent_ids)
            related_items = sum([[i for i, v in c] for c in list(children.values())], [])
            parents = defaultdict(lambda: [])
            for parent, childs in list(children.items()):
                for child, v in childs:
                    parents[child].append((parent, v))

        answers_num = environment.number_of_answers_more_items(user=user, items=related_items)
        last_answer_time = environment.last_answer_time_more_items(user=user, items=related_items)
        probability = self.get_predictions(environment, user, items, time)
        last_answer_time_parents = self._last_answer_time_for_parents(environment, parents, last_answer_time)
        answers_num_parents = self._answers_num_for_parents(environment, parents, answers_num)
        prob_target = self.get_target_probability(environment, user, practice_context=practice_context)

        if proso.django.log.is_active():
            for item in items:
                if len(parents.get(item, [])) == 0:
                    LOGGER.warn("The item %s has no parent" % item)

        def _score(item):
            return (
                self._weight_probability * self._score_probability(prob_target, probability[item]) +
                self._weight_time_ago * self._score_last_answer_time(last_answer_time[item], time) +
                self._weight_number_of_answers * self._score_answers_num(answers_num[item]),
                random.random()
            )

        def _finish_score(xxx_todo_changeme):
            ((score, r), i) = xxx_todo_changeme
            total = 0.0
            parent_time_score = 0.0
            parent_answers_num_score = 0.0
            for p, v in parents[i]:
                parent_time_score += v * self._score_last_answer_time(last_answer_time_parents[p], time)
                parent_answers_num_score += v * self._score_answers_num(answers_num_parents[p])
                total += 1
            if total > 0:
                parent_time_score = parent_time_score / total
                parent_answers_num_score = parent_answers_num_score / total
            score += self._weight_parent_time_ago * parent_time_score
            score += self._weight_parent_number_of_answers * parent_answers_num_score
            return (score, r), i

        scored = [(_score(item), item) for item in items]
        if self._recompute_parent_score:
            candidates = []
            while len(candidates) < n and len(scored) > 0:
                finished = list(map(_finish_score, scored))
                score, chosen = max(finished)
                if proso.django.log:
                    LOGGER.debug(
                        'selecting %s (total_score %.2f, prob: %.4f, prob score %.2f, time: %s, time_score %.2f, answers: %s, answers score %.2f, parents %s)' %
                        (
                            chosen, score[0],
                            probability[chosen],
                            self._weight_probability * self._score_probability(prob_target, probability[chosen]),
                            last_answer_time[chosen],
                            self._weight_time_ago * self._score_last_answer_time(last_answer_time[chosen], time),
                            answers_num[chosen],
                            self._weight_number_of_answers * self._score_answers_num(answers_num[chosen]),
                            [x[0] for x in parents[chosen]])
                    )
                candidates.append(chosen)
                for p, v in parents[chosen]:
                    last_answer_time_parents[p] = time
                scored = [score_i for score_i in scored if score_i[1] != chosen]
        else:
            candidates = [score_r_i[1] for score_r_i in sorted(scored, reverse=True)[:min(len(scored), n)]]

        return candidates, [None for _ in candidates]

    def _score_answers_num(self, answers_num):
        return 0.5 / max(math.sqrt(answers_num), 0.5)

    def _score_probability(self, target_probability, probability):
        diff = target_probability - probability
        sign = 1 if diff > 0 else -1
        normed_diff = abs(diff) / max(0.001, abs(target_probability - 0.5 + sign * 0.5))
        return 1 - normed_diff ** 2

    def _score_last_answer_time(self, last_answer_time, time):
        if last_answer_time is None:
            return 0.0
        seconds_ago = (time - last_answer_time).total_seconds()
        if seconds_ago <= 0:
            return -1.0
        return -1 + numpy.log2(min(seconds_ago, self._time_ago_max)) / numpy.log2(self._time_ago_max)

    def _answers_num_for_parents(self, environment, parents, answers_num):
        children = defaultdict(list)
        for i, ps in parents.items():
            for p, v in ps:
                children[p].append(i)

        return dict([(p_chs[0], sum([answers_num[ch] for ch in p_chs[1]])) for p_chs in list(children.items())])

    def _last_answer_time_for_parents(self, environment, parents, last_answer_time):
        children = defaultdict(list)
        for i, ps in parents.items():
            for p, v in ps:
                children[p].append(i)

        def _max_time_from_items(xs):
            times = [x for x in [last_answer_time[x] for x in xs] if x is not None]
            if len(times) > 0:
                return max(times)
            else:
                return None

        return dict([(p_chs1[0], _max_time_from_items(p_chs1[1])) for p_chs1 in list(children.items())])

    def __str__(self):
        return 'SCORE BASED ITEM SELECTION: target probability {0:.2f}, weight probability {1:.2f}, weight time {2:.2f}, weight answers {3:.2f}'.format(
            self._target_probability, self._weight_probability, self._weight_time_ago, self._weight_number_of_answers)


def adjust_target_probability(target_probability, rolling_success):
    if rolling_success is None:
        return target_probability
    norm = 1 - target_probability if rolling_success > target_probability else target_probability
    correction = ((target_probability - rolling_success) / max(0.001, norm)) * (1 - norm)
    return target_probability + correction


class ContextBasedItemSelection(ScoreItemSelection):
    def __init__(self, predictive_model, weight_probability=10.0, weight_number_of_answers=5.0, weight_time_ago=5,
                 weight_parent_time_ago=5.0, weight_parent_number_of_answers=2.5,
                 target_probability=DEFAULT_TARGET_PROBABILITY, time_ago_max=120, recompute_parent_score=True,
                 history_adjustment=True, estimate_parent_factors=True):
        from proso.django.request import get_current_request
        from proso_models.models import get_filter
        from proso_concepts.models import Concept

        req = get_current_request()

        categories = get_filter(req)
        categories = list(set().union(*categories))
        categories.sort(reverse=True)
        category_identifier = Concept.objects.filter(query=json.dumps([categories])).first().identifier

        LOGGER.debug("REQUEST FILTERS: %s" % json.dumps([categories]))
        LOGGER.debug("REQUEST FILTER -> CATEGORY_IDENTIFIER: %s" % category_identifier)

        if category_identifier in ["9286c11ae03051824142", "0abbc00aab49f3ab3087", "e7576f2d7d9acdc8938d",
                                   "e0a6b9187f402bc4b6b4", "5003410ef72a80a76ab8", "6b799a540d42f7164d57",
                                   "777959a7e2799da678ce", "32110d4fd300c32b6dda", "b239ffe83950753eff4b",
                                   "55dfd24083b6c5248539", "0c74a5bff211f8c1366b", "176c56aa2399180149c0",
                                   "3f987d036bf3b84033c6", "cf3e1afe7556fc9b5302"]:
            target_probability = 0.80
        elif category_identifier in ["5d96cf6829a091825ab1", "07907708da836f3e41c0", "88775c0f18142298fdab",
                                     "99b2a9bd43cd5226eec1", "dd326eccb76dbfae6dd1", "09b896106800eb5f1931",
                                     "149c12764fe26ebcf685"]:
            target_probability = 0.50
        else:
            target_probability = 0.65

        LOGGER.debug("REQUEST FILTER -> USING TARGET_PROBABILITY == %f" % target_probability)

        super().__init__(predictive_model, weight_probability, weight_number_of_answers, weight_time_ago,
                         weight_parent_time_ago, weight_parent_number_of_answers, target_probability, time_ago_max,
                         recompute_parent_score, history_adjustment, estimate_parent_factors)

    def __str__(self):
        return 'CONTEXT BASED ITEM SELECTION: target probability {0:.2f}, weight probability {1:.2f}, weight time {2:.2f}, weight answers {3:.2f}'.format(
            self._target_probability, self._weight_probability, self._weight_time_ago, self._weight_number_of_answers)
