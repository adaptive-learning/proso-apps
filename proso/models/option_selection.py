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

    def __init__(self, item_selector, **kwargs):
        self._item_selector = item_selector

    @abc.abstractmethod
    def select_options(self, environment, user, item, time, options, **kwargs):
        pass

    def select_options_more_items(self, environment, user, items, time, options, **kwargs):
        return [self.select_options(environment, user, item, time, options[item], **kwargs)
                for item in items]


class NonOptionSelection(OptionSelection):
    def select_options(self, environment, user, item, time, options, **kwargs):
        return []


class RandomOptionSelection(OptionSelection):
    def select_options(self, environment, user, item, time, options, **kwargs):
        if item in options:
            options.remove(item)
        return random.sample(options, min(len(options), random.randint(1, 5))) + [item]


class ConfusingOptionSelection(OptionSelection):
    def __init__(self, item_selector, max_options=6, allow_zero_options_restriction=False, **kwargs):
        super(ConfusingOptionSelection, self).__init__(item_selector, **kwargs)
        self.max_options = max_options
        self.allow_zero_options_restriction = allow_zero_options_restriction

    def select_options_more_items(self, environment, user, items, time, options, allow_zero_options=None, **kwargs):
        if allow_zero_options is None:
            allow_zero_options = defaultdict(lambda: True)
        return [self.select_options(environment, user, item, time, options[item],
                                    allow_zero_options=allow_zero_options[item], **kwargs) for item in items]

    def select_options(self, environment, user, item, time, options, allow_zero_options=True, **kwargs):
        rolling_success = self._item_selector.get_rolling_success()
        target_probability = self._item_selector.get_target_probability()
        prediction = self._item_selector.get_prediction_for_selected_item(item)
        if prediction is None:
            raise ValueError("Prediction is missing")

        # number of options
        round_fun = round
        prob_real = prediction
        prob_target = adjust_target_probability(target_probability, rolling_success)
        g = min(0.5, max(0, prob_target - prob_real) / max(0.001, 1 - prob_real))
        k = round_fun(1.0 / g) if g != 0 else 1
        number_of_options = int(0 if (k > self.max_options or k == 0) else (k - 1))
        if number_of_options == 0:
            if not self.allow_zero_options_restriction or allow_zero_options:
                return []
            else:
                number_of_options = self.max_options
        # confusing places
        confusing_factor = environment.confusing_factor_more_items(item, options)
        confusing_places = map(
            lambda (a, b): (b, a + 1),
            sorted(zip(confusing_factor, options), reverse=True)
        )
        confusing_factor_total = float(sum(confusing_factor) + len(confusing_places))
        # options
        result_options = []
        for i in range(number_of_options):
            prob_sum = 0
            random_dice = random.uniform(0, confusing_factor_total)
            for i, conf_factor in confusing_places:
                if i in result_options or i == item:
                    continue
                prob_sum += conf_factor
                if random_dice > prob_sum:
                    result_options.append(i)
                    confusing_factor_total -= conf_factor
                    break
        return result_options + [item]


################################################################################
# Tests
################################################################################

class TestOptionSelection(unittest.TestCase):

    def test_questions_with_one_option_are_forbidden(self):
        # setup
        options = range(1, 101)
        confusing_factors = [0] * 100
        # mock item selector
        item_selector = MagicMock()
        item_selector.get_rolling_success.return_value = 0.5
        item_selector.get_target_probability.return_value = 0.75
        item_selector.get_prediction_for_selected_item.return_value = 0.5
        # mock environment
        environment = MagicMock()
        environment.confusing_factor_more_items.return_value = confusing_factors
        # test
        option_selector = self.get_option_selector(item_selector)
        selected = option_selector.select_options(environment, 0, 0, None, options)
        self.assertNotEqual(1, len(selected), 'There is no question with one option.')
        selected = option_selector.select_options_more_items(
            environment, 0, range(100, 110), None, dict(zip(range(100, 110), ([options] * 10))))
        for opts in selected:
            self.assertNotEqual(1, len(opts), 'There is no question with one option.')


    @abc.abstractmethod
    def get_option_selector(self, item_selector):
        pass
