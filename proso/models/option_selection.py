import abc
import logging
import random
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

    def select_options(self, environment, user, item, time, options, **kwargs):
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
        number_of_options = int(0 if (k > 6 or k == 0) else (k - 1))
        if number_of_options == 0:
            return []
        # confusing places
        confusing_factor = environment.confusing_factor_more_items(item, options)
        confusing_factor_total = float(sum(confusing_factor))
        confusing_places = map(lambda (a, b): (b, a),
                               sorted(zip(confusing_factor, options), reverse=True))
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
