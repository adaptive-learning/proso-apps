import abc
from collections import defaultdict
import logging
import random
import unittest
from mock import MagicMock

from proso.models.item_selection import adjust_target_probability


LOGGER = logging.getLogger('django.request')


class OptionSelection:
    __metaclass__ = abc.ABCMeta

    def __init__(self, item_selector, max_options=6, allow_zero_options_restriction=False, **kwargs):
        self._item_selector = item_selector
        self._allow_zero_options_restriction = allow_zero_options_restriction
        self._max_options = max_options

    @abc.abstractmethod
    def select_options(self, environment, user, item, time, options, **kwargs):
        pass

    def select_options_more_items(self, environment, user, items, time, options, allow_zero_options=None, **kwargs):
        if allow_zero_options is None:
            allow_zero_options = defaultdict(lambda: True)
        return [self.select_options(environment, user, item, time, options[item],
                                    allow_zero_options=allow_zero_options[item], **kwargs) for item in items]

    def is_zero_options_restriction_allowed(self):
        return self._allow_zero_options_restriction

    def max_options(self):
        return self._max_options


class NonOptionSelection(OptionSelection):
    def select_options(self, environment, user, item, time, options, **kwargs):
        return []


class RandomOptionSelection(OptionSelection):

    def select_options(self, environment, user, item, time, options, allow_zero_options=None, **kwargs):
        if len(options) == 0:
            if self.is_zero_options_restriction_allowed() and not allow_zero_options:
                raise Exception("Zero options are not allowed, but there are no candidates for options in case of item {}.".format(item))
            else:
                return []
        if item in options:
            options.remove(item)
        number_of_options = min(len(options), random.randint(0, self.max_options() - 1))
        if number_of_options == 0:
            if not self.is_zero_options_restriction_allowed() or allow_zero_options:
                return []
            else:
                number_of_options = self.max_options() - 1
        return random.sample(options, min(len(options), number_of_options)) + [item]


class ConfusingOptionSelection(OptionSelection):

    def select_options(self, environment, user, item, time, options, allow_zero_options=True, **kwargs):
        options = filter(lambda i: i != item, options)
        if len(options) == 0:
            if self.is_zero_options_restriction_allowed() and not allow_zero_options:
                raise Exception("Zero options are not allowed, but there are no candidates for options in case of item {}.".format(item))
            else:
                return []
        rolling_success = self._item_selector.get_rolling_success(environment, user, None)
        target_probability = self._item_selector.get_target_probability()
        prediction = self._item_selector.get_predictions(environment)[item]
        if prediction is None:
            raise ValueError("Prediction is missing")

        # number of options
        round_fun = round
        prob_real = prediction
        prob_target = adjust_target_probability(target_probability, rolling_success)
        g = min(0.5, max(0, prob_target - prob_real) / max(0.001, 1 - prob_real))
        k = round_fun(1.0 / g) if g != 0 else 1
        number_of_options = min(len(options), int(0 if (k > self.max_options() or k == 0) else (k - 1)))
        if number_of_options == 0:
            if not self.is_zero_options_restriction_allowed() or allow_zero_options:
                return []
            else:
                number_of_options = self.max_options() - 1
        # confusing places
        confusing_factor = environment.confusing_factor_more_items(item, options)
        confusing_items = map(
            lambda (a, b): (b, a + 1),
            sorted(zip(confusing_factor, options), reverse=True)
        )
        confusing_factor_total = float(sum(confusing_factor) + len(confusing_items))
        # options
        result_options = []
        for i in range(number_of_options):
            prob_sum = 0
            random_dice = random.uniform(1, confusing_factor_total)
            for i, conf_factor in confusing_items:
                if i in result_options:
                    continue
                prob_sum += conf_factor
                if random_dice <= prob_sum:
                    result_options.append(i)
                    confusing_factor_total -= conf_factor
                    break
        if len(result_options) == 0:
            raise Exception('There are no options for multiple-choice question! Number of options set to: {}, confusing factors {}'.format(number_of_options, confusing_items))
        if len(set(result_options)) != len(result_options):
            raise Exception('There are some options more times for multiple-choice question! Number of options set to: {}, confusing factors {}'.format(number_of_options, confusing_items))
        return result_options + [item]


################################################################################
# Tests
################################################################################

class TestOptionSelection(unittest.TestCase):

    def test_questions_with_low_number_of_options(self):
        for i in xrange(3):
            # setup
            options = range(1, i + 1)
            environment = self.get_environment([0] * 100)
            # test
            option_selector = self.get_option_selector(self.get_item_selector(0.75, 0.5))
            selected = option_selector.select_options(environment, 0, 0, None, options)
            self.assertNotEqual(1, len(selected), 'There is no question with one option.')
            if len(selected) > 0:
                self.assertTrue(0 in selected, "The asked item is in options in case of non-zero options.")

    def test_questions_with_one_option_are_forbidden(self):
        # setup
        options = range(1, 101)
        environment = self.get_environment([0] * 100)
        # test
        option_selector = self.get_option_selector(self.get_item_selector(0.75, 0.5))
        selected = option_selector.select_options(environment, 0, 0, None, options)
        self.assertNotEqual(1, len(selected), 'There is no question with one option.')
        selected = option_selector.select_options_more_items(
            environment, 0, range(100, 110), None, dict(zip(range(100, 110), ([options] * 10))))
        for i, opts in zip(range(100, 110), selected):
            self.assertNotEqual(1, len(opts), 'There is no question with one option.')
            if len(opts) > 0:
                self.assertTrue(i in opts, "The asked item is in options in case of non-zero options.")

    def get_environment(self, confusing_factors):
        environment = MagicMock()
        environment.confusing_factor_more_items.return_value = confusing_factors
        return environment

    def get_item_selector(self, target_probability, rolling_success):
        item_selector = MagicMock()
        item_selector.get_rolling_success.return_value = rolling_success
        item_selector.get_target_probability.return_value = target_probability
        return item_selector



    @abc.abstractmethod
    def get_option_selector(self, item_selector):
        pass
