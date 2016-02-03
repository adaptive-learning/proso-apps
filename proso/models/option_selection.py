import abc
from collections import defaultdict
import logging
import random
import proso.rand
import math
import unittest
import numpy
from mock import MagicMock

from proso.models.item_selection import adjust_target_probability


LOGGER = logging.getLogger('django.request')


################################################################################
# API
################################################################################

class OptionSelection(metaclass=abc.ABCMeta):

    def __init__(self, item_selector, options_number, **kwargs):
        self._item_selector = item_selector
        self._options_number = options_number

    def item_selector(self):
        return self._item_selector

    def options_number(self):
        return self._options_number

    def select_options(self, environment, user, item, time, options, allow_zero_options=True, **kwargs):
        return self.select_options_more_items(
            environment, user, [item], time, {item: allow_zero_options}, **kwargs
        )

    def select_options_more_items(self, environment, user, items, time, options, allow_zero_options=None, **kwargs):
        if allow_zero_options is None:
            allow_zero_options = defaultdict(lambda: True)
        predictions = self._item_selector.get_predictions(environment)
        target_probability = self._item_selector.get_target_probability(environment, user, None)
        result = []
        for item in items:
            prediction = predictions[item]
            if prediction is None:
                raise ValueError("Prediction for item {} is missing.".format(item))
            number_of_options = self.options_number().get_number_of_options(target_probability, prediction, allow_zero_options[item], len(options[item]))
            if number_of_options == 0:
                result.append([])
                continue
            confusing_factors = dict(zip(options[item], environment.confusing_factor_more_items(item, options[item])))
            result_options = self.compute_options(target_probability, prediction, number_of_options, confusing_factors)
            if len(result_options) != number_of_options:
                raise Exception('There is a wrong number of options for multiple-choice question! Number of options set to: {}, confusing factors {}'.format(number_of_options, confusing_factors))
            if len(set(result_options)) != number_of_options:
                raise Exception('There are some options more times for multiple-choice question! Number of options set to: {}, confusing factors {}'.format(number_of_options, confusing_factors))
            result.append(result_options + [item])
        return result

    @abc.abstractmethod
    def compute_options(self, target_probability, prediction, number_of_options, confusing_factors):
        pass


class OptionsNumber(metaclass=abc.ABCMeta):

    def __init__(self, max_options=6, allow_zero_options_restriction=True):
        self._max_options = max_options
        self._allow_zero_options_restriction = allow_zero_options_restriction

    def is_zero_options_restriction_allowed(self):
        return self._allow_zero_options_restriction

    def get_max_options(self):
        return self._max_options

    def get_number_of_options(self, target_probability, prediction, allow_zero_options, options_available):
        if options_available == 0:
            if self.is_zero_options_restriction_allowed() and not allow_zero_options:
                raise Exception("Zero options are not allowed, but there are no candidates for options in case of item {}.".format(item))
            else:
                return 0
        number_of_options = self.compute_number_of_options(target_probability, prediction)
        if number_of_options == 0:
            if not self.is_zero_options_restriction_allowed() or allow_zero_options:
                number_of_options = 0
            else:
                number_of_options = self.get_max_options() - 1
        return min(options_available, number_of_options)

    @abc.abstractmethod
    def compute_number_of_options(self, target_probability, prediction):
        pass


################################################################################
# Number of distractors
################################################################################

class FullyRandomOptionsNumber(OptionsNumber):

    def compute_number_of_options(self, target_probability, prediction):
        return random.randint(0, self.get_max_options() - 1)


class PartiallyRandomOptionsNumber(OptionsNumber):

    def compute_number_of_options(self, target_probability, prediction):
        if prediction > target_probability:
            return 0
        else:
            return random.randint(0, self.get_max_options() - 1)


class AdjustedOptionsNumber(OptionsNumber):

    def compute_number_of_options(self, target_probability, prediction):
        round_fun = round
        g = min(0.5, max(0, target_probability - prediction) / max(0.00001, 1 - prediction))
        k = round_fun(1.0 / g) if g != 0 else 1
        return int(0 if (k > self.get_max_options() or k == 0) else (k - 1))


class UniformlyAdjustedOptionsNumber(OptionsNumber):

    def compute_number_of_options(self, target_probability, prediction):
        if prediction > target_probability:
            return 0
        else:
            return max(int(math.ceil((prediction / max(target_probability, 0.00001)) * (self.get_max_options() - 1))), 1)


class ZeroOptionsNumber(OptionsNumber):

    def compute_number_of_options(self, target_probability, prediction):
        return 0


class ConstantOptionsNumber(OptionsNumber):

    def __init__(self, number_of_options, max_options=6, allow_zero_options_restriction=True):
        OptionsNumber.__init__(self, max_options=max_options, allow_zero_options_restriction=allow_zero_options_restriction)
        self._number_of_options = number_of_options

    def compute_number_of_options(self, target_probability, prediction):
        return self._number_of_options


################################################################################
# Selection of distractors
################################################################################

class RandomOptionSelection(OptionSelection):

    def compute_options(self, target_probability, prediction, number_of_options, confusing_factors):
        return random.sample(confusing_factors.keys(), number_of_options)


class CompetitiveOptionSelection(OptionSelection):

    def compute_options(self, target_probability, prediction, number_of_options, confusing_factors):
        return proso.rand.roulette(
            {key: val + 1 for (key, val) in confusing_factors.items()},
            number_of_options
        )



################################################################################
# Tests
################################################################################

class TestOptionsNumber(unittest.TestCase):

    def test_number_of_options(self):
        max_options = 6
        for target_probability in numpy.linspace(0, 1, 6):
            for prediction in numpy.linspace(0, 1, 6):
                for options_available in [2, 100]:
                        number_of_options = self.get_options_number(max_options, True).get_number_of_options(
                            target_probability, prediction, True, options_available)
                        self.assertTrue(number_of_options >= 0)
                        self.assertTrue(number_of_options <= options_available)
                        self.assertTrue(number_of_options <= max_options)
                        number_of_options = self.get_options_number(max_options, True).get_number_of_options(
                            target_probability, prediction, False, options_available)
                        self.assertTrue(number_of_options > 0)
                        self.assertTrue(number_of_options <= options_available)
                        self.assertTrue(number_of_options <= max_options)

    @abc.abstractmethod
    def get_options_number(self, max_options, allow_zero_options_restriction):
        pass


class TestOptionSelection(unittest.TestCase):

    def test_compute_options(self):
        confusing_factors = dict(zip(range(100), [1 + 10 * x for x in range(100)]))
        for target_probability in numpy.linspace(0, 1, 6):
            for prediction in numpy.linspace(0, 1, 6):
                for number_of_options in [1, 3, 5]:
                    option_selector = self.get_option_selector(
                        self.get_item_selector(0.75),
                        ConstantOptionsNumber(number_of_options)
                    )
                    options = option_selector.compute_options(target_probability, prediction, number_of_options, confusing_factors)
                    self.assertEqual(len(set(options) - set(confusing_factors.keys())), 0)
                    self.assertEqual(len(set(options)), number_of_options)

    def get_item_selector(self, target_probability):
        item_selector = MagicMock()
        item_selector.get_target_probability.return_value = target_probability
        item_selector.get_predictions.return_value = defaultdict(lambda: 0.5)
        return item_selector

    @abc.abstractmethod
    def get_option_selector(self, item_selector, options_number):
        pass
