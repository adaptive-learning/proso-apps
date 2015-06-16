import abc
import operator
from math import exp


class PredictiveModel:

    """
    This class handles the logic behind the predictive models, which is
    divided into 3 phases:
        prepare:
            the model loads the necessary data from the environment
        predict
            the model uses the loaded data to predict the correctness of the answer
        update
            the model updates environment to persist it for the future prediction
    """

    __metaclass__ = abc.ABCMeta

    def predict_more_items(self, environment, user, items, time, **kwargs):
        data = self.prepare_phase_more_items(environment, user, items, time, **kwargs)
        return self.predict_phase_more_items(data, user, items, time, **kwargs)

    def predict(self, environment, user, item, time, **kwargs):
        data = self.prepare_phase(environment, user, item, time, **kwargs)
        return self.predict_phase(data, user, item, time, **kwargs)

    def predict_and_update(self, environment, user, item, correct, time, **kwargs):
        data = self.prepare_phase(environment, user, item, time, **kwargs)
        prediction = self.predict_phase(data, user, item, time, **kwargs)
        self.update_phase(
            environment, data, prediction, user, item, correct, time, **kwargs)
        return prediction

    @abc.abstractmethod
    def prepare_phase(self, environment, user, item, time, **kwargs):
        """
        In this phase, the predictive model touches the environment, loads all
        necessary data and returns it.

        Args:
            environment (proso.models.environment.Environment):
                environment where all the important data are persist
            user (int):
                identifier of the user answering the question
            item (int):
                identifier of the question item
            time (datetime.datetime):
                datetime when the question is asked
            kwargs:
                used for other information about the question

        Returns:
            object
        """
        pass

    @abc.abstractmethod
    def prepare_phase_more_items(self, environment, user, items, time, **kwargs):
        pass

    @abc.abstractmethod
    def predict_phase(self, data, user, item, time, **kwargs):
        """
        Uses the data from prepare phase and tries to predict the probability
        of the correct answer. That means the prediction for the user and the
        asked item before the given answer is processed.

        Args:
            data (object):
                data from the prepare phase
            user (int):
                identifier of the user answering the question
            item (int):
                identifier of the question item
            time (datetime.datetime):
                datetime when the question is asked
            kwargs:
                used for other information about the question

        Returns:
            float:
                the number from [0, 1] representing the probability of the
                correct answer
        """
        pass

    @abc.abstractmethod
    def predict_phase_more_items(self, data, user, items, time, **kwargs):
        pass

    @abc.abstractmethod
    def update_phase(self, environment, data, prediction, user, item, correct, time, **kwargs):
        """
        After the prediction update the environment and persist some
        information for the predictive model.

        Args:
            environment (proso.models.environment.Environment):
                environment where all the important data are persist
            data (object):
                data from the prepare phase
            user (int):
                identifier of the user answering the question
            item (int):
                identifier of the question item
            correct (bool):
                corretness of the answer
        """
        pass


class SimplePredictiveModel(PredictiveModel):

    """
    Predictive model which doesn't force you to use environment.
    """

    def prepare_phase(self, environment, user, item, time, **kwargs):
        return None

    def prepare_phase_more_items(self, environment, user, items, time, **kwargs):
        return None

    def predict_phase(self, data, user, item, time, **kwargs):
        return self.simple_predict(user, item, time, **kwargs)

    def predict_phase_more_items(self, data, user, items, time, **kwargs):
        return [self.simple_predict(user, item, time, **kwargs) for item in items]

    def update_phase(self, environment, data, prediction, user, item, correct, time, **kwargs):
        self.simple_update(prediction, user, item, correct, time, **kwargs)

    @abc.abstractmethod
    def simple_predict(self, user, item, time, **kwargs):
        pass

    @abc.abstractmethod
    def simple_update(self, prediction, user, item, correct, time, **kwargs):
        pass


class AveragePredictiveModel(PredictiveModel):

    def prepare_phase(self, environment, user, item, time, **kwargs):
        total_sum = environment.read('total_sum', item=item, default=0)
        number_of_answers = environment.number_of_answers(item=item)
        return total_sum, number_of_answers

    def prepare_phase_more_items(self, environment, user, items, time, **kwargs):
        total_sums = environment.read_more_items('total_sum', items=items, default=0)
        number_of_answers = environment.number_of_answers_more_items(items=items)
        return total_sums, number_of_answers

    def predict_phase(self, data, user, item, time, **kwargs):
        return float(data[0]) / max(data[1], 1)

    def predict_phase_more_items(self, data, user, items, time, **kwargs):
        return map(lambda (tot, num): float(tot) / max(num, 1), zip(data[0], data[1]))

    def update_phase(self, environment, data, prediction, user, item, correct, time, **kwargs):
        environment.update('total_sum', 0, lambda x: x + correct, item=item)


class PriorCurrentPredictiveModel(PredictiveModel):

    def __init__(self, time_shift=80.0, pfae_good=3.4, pfae_bad=0.3, elo_alpha=0.8, elo_dynamic_alpha=0.05):
        self._time_shift = time_shift
        self._pfae_good = pfae_good
        self._pfae_bad = pfae_bad
        self._elo_alpha = elo_alpha
        self._elo_dynamic_alpha = elo_dynamic_alpha

    def prepare_phase(self, environment, user, item, time, **kwargs):
        result = {}
        result['prior_skill'] = environment.read('prior_skill', user=user, default=0)
        result['difficulty'] = environment.read('difficulty', item=item, default=0)
        result['current_skill'] = environment.read('current_skill', user=user, item=item)
        result['use_prior'] = result['current_skill'] is None
        if result['use_prior']:
            result['user_first_answers'] = environment.number_of_first_answers(user=user)
            result['item_first_answers'] = environment.number_of_first_answers(item=item)
        else:
            result['last_time'] = environment.last_answer_time(user=user, item=item)
        return result

    def prepare_phase_more_items(self, environment, user, items, time, **kwargs):
        result = {}
        result['prior_skill'] = environment.read('prior_skill', user=user, default=0)
        result['difficulties'] = environment.read_more_items('difficulty', items=items, default=0)
        result['current_skills'] = environment.read_more_items('current_skill', user=user, items=items)
        result['last_times'] = environment.last_answer_time_more_items(user=user, items=items)
        return result

    def predict_phase(self, data, user, item, time, **kwargs):
        if data['current_skill'] is None:
            skill = data['prior_skill'] - data['difficulty']
        else:
            seconds_ago = (time - data['last_time']).total_seconds() if data['last_time'] else 315460000
            skill = data['current_skill'] + self._time_shift / max(seconds_ago, 0.001)
        return predict_simple(
            skill,
            number_of_options=len(kwargs['options']) if 'options' in kwargs else 0,
            guess=kwargs.get('guess'))[0]

    def predict_phase_more_items(self, data, user, items, time, **kwargs):
        preds = []
        to_iter = zip(
            items, data['difficulties'],
            data['current_skills'], data['last_times'])
        for i, d, c, t in to_iter:
            preds.append(self.predict_phase({
                'prior_skill': data['prior_skill'],
                'difficulty': d,
                'current_skill': c,
                'last_time': t
            }, user, i, time, **kwargs))
        return preds

    def update_phase(self, environment, data, prediction, user, item, correct, time, **kwargs):
        result = correct
        if data['current_skill'] is None:
            current_skill = data['prior_skill'] - data['difficulty']
        else:
            current_skill = data['current_skill']
        if result:
            current_skill = current_skill + self._pfae_good * (result - prediction)
        else:
            current_skill = current_skill + self._pfae_bad * (result - prediction)
        environment.write('current_skill', current_skill, user=user, item=item, time=time)
        if data['use_prior']:
            alpha_fun = lambda n: self._elo_alpha / (1 + self._elo_dynamic_alpha * n)
            prior_skill_alpha = alpha_fun(data['user_first_answers'])
            difficulty_alpha = alpha_fun(data['item_first_answers'])
            environment.write(
                'prior_skill', data['prior_skill'] + prior_skill_alpha * (result - prediction), user=user, time=time)
            environment.write(
                'difficulty', data['difficulty'] - difficulty_alpha * (result - prediction), item=item, time=time)


class AlwaysLearningPredictiveModel(PredictiveModel):

    def __init__(self, pfae_good=1.0, pfae_bad=0.5, elo_alpha=0.8, elo_dynamic_alpha=0.05):
        self._pfae_good = pfae_good
        self._pfae_bad = pfae_bad
        self._elo_alpha = elo_alpha
        self._elo_dynamic_alpha = elo_dynamic_alpha

    def prepare_phase(self, environment, user, item, time, **kwargs):
        return self.prepare_phase_more_items(environment, user, [item], time, **kwargs)

    def prepare_phase_more_items(self, environment, user, items, time, **kwargs):
        parents = self._load_parents(environment, items, user)
        all_items = list(set(items + [i for ps in parents.values() for (i, v) in ps]))
        return {
            'skills': dict(zip(
                all_items, environment.read_more_items('skill', items=all_items, user=user, default=0))),
            'first_answers': dict(zip(
                items, environment.number_of_first_answers_more_items(items=items))),
            'difficulties': dict(zip(
                items, environment.read_more_items('difficulty', items=items, default=0))),
            'last_times': dict(zip(
                items, environment.last_answer_time_more_items(items=items, user=user))),
            'parents': parents
        }

    def predict_phase(self, data, user, item, time, **kwargs):
        skill = self._load_skill(item, data)
        difficulty = data['difficulties'][item]
        return predict_simple(
            self._load_skill(parent, data) - difficulty,
            number_of_options=len(kwargs['options']) if 'options' in kwargs else 0,
            guess=kwargs.get('guess'))[0]

    def predict_phase_more_items(self, data, user, items, time, **kwargs):
        return map(lambda i: self.predict_phase(data, user, i, time, **kwargs), items)

    def update_phase(self, environment, data, prediction, user, item, correct, time, **kwargs):
        if data['last_times'][item] is None:
            alpha_fun = lambda n: self._elo_alpha / (1 + self._elo_dynamic_alpha * n)
            difficulty_alpha = alpha_fun(data['first_answers'][item])
            data['difficulties'][item] -= difficulty_alpha * (correct - prediction)
            environment.write('difficulty', data['difficulties'][item], item=item, time=time)
        parents_per_level = [
            list(set(map(lambda (i, w): i, parents))) for parents in self._iterate_parents_per_level(item, data)]
        parents_per_level = zip(range(len(parents_per_level)), parents_per_level)
        parents_per_level.reverse()
        level_decay = lambda level: 1.0 / 3 ** level
        update_const = self._pfae_good if correct else self._pfae_bad
        difficulty = data['difficulties'][item]
        for level, parents in parents_per_level:
            for parent in parents:
                parent_prediction = predict_simple(
                    self._load_skill(parent, data) - difficulty,
                    number_of_options=len(kwargs['options']) if 'options' in kwargs else 0,
                    guess=kwargs.get('guess'))[0]
                data['skills'][parent] += level_decay(level) * update_const * (correct - parent_prediction)
                environment.write('skill', data['skills'][parent], item=parent, user=user, time=time)

    def _load_parents(self, environment, items, user):
        parents = {}
        while len(items) > 0:
            found = environment.get_items_with_values_more_items('parent', items)
            new_items = set()
            for i, ps in zip(items, found):
                new_items = new_items.union(map(lambda x: x[0], ps))
                if len(ps) == 0:
                    ps.append((None, 1))
                parents[i] = ps
            items = list(new_items)
        return parents

    def _load_skill(self, item, data):
        skill = 0
        for skill_items in self._iterate_parents_per_level(item, data):
            weights = float(sum(map(lambda (i, w): w, skill_items)))
            skill += sum(map(lambda (i, w): data['skills'][i] * w / weights, skill_items))
        return skill

    def _iterate_parents_per_level(self, item, data):
        to_find = [(item, 1)]
        while len(to_find) > 0:
            yield to_find
            to_find = [iw for ps in map(lambda (i, w): [] if i is None else data['parents'][i], to_find) for iw in ps]


class ShiftedPredictiveModel(PredictiveModel):

    def __init__(self, predictive_model, prediction_shift):
        self._predictive_model = predictive_model
        self._prediction_shift = prediction_shift

    def predict_phase_more_items(self, data, user, items, time, **kwargs):
        return super(ShiftedPredictiveModel, self).predict_phase_more_items(data, user, items, time, **kwargs)

    def prepare_phase(self, environment, user, item, time, **kwargs):
        return super(ShiftedPredictiveModel, self).prepare_phase(environment, user, item, time, **kwargs)

    def prepare_phase_more_items(self, environment, user, items, time, **kwargs):
        return super(ShiftedPredictiveModel, self).prepare_phase_more_items(environment, user, items, time, **kwargs)

    def predict(self, environment, user, item, time, **kwargs):
        return super(ShiftedPredictiveModel, self).predict(environment, user, item, time, **kwargs) + self._prediction_shift

    def predict_phase(self, data, user, item, time, **kwargs):
        return super(ShiftedPredictiveModel, self).predict_phase(data, user, item, time, **kwargs)

    def update_phase(self, environment, data, prediction, user, item, correct, time, **kwargs):
        return super(ShiftedPredictiveModel, self).update_phase(
            environment, data, prediction, user, item, correct, time, **kwargs)

    def predict_and_update(self, environment, user, item, correct, time, **kwargs):
        return super(ShiftedPredictiveModel, self).predict_and_update(environment, user, item, correct, time, **kwargs)

    def predict_more_items(self, environment, user, items, time, **kwargs):
        return map(
            lambda p: min(1.0, max(0.0, p + self._prediction_shift)),
            super(ShiftedPredictiveModel, self).predict_more_items(environment, user, items, time, **kwargs))


def predict_simple(skill_asked, number_of_options=None, guess=None):
    if guess is None and number_of_options is None:
        raise Exception('Either guess parameter or number of options has to be specified.')
    if guess is None:
        guess = 0.0
        if number_of_options:
            guess = 1.0 / number_of_options
    return (guess + (1 - guess) * _sigmoid(skill_asked), [])


def predict(skill_asked, option_skills):
    """
    Returns the probability of correct answer.

    Args:
        skill_asked (float):
            number representing a knowledge of the given user for the asked
            item
        option_skills ([float]):
            list of numbers representing a knowledge for the options

    Returns:
        (float, [float]):
            probability of the correct answer for the asked item
            and the probabilities for the options they will be answered instead
            of the asked item
    """

    if len(option_skills) == 0:
        return (_sigmoid(skill_asked), [])

    probs = map(lambda x: _sigmoid(x), [skill_asked] + option_skills)
    items = 2 ** len(probs)
    asked_prob = 0
    opt_wrong_probs = [0 for i in option_skills]

    for i in range(items):
        knows = _to_binary_reverse_list(i, len(probs))
        guess_options = 1 if knows[0] else sum(map(lambda x: 1 - x, knows))
        current_prob = reduce(
            operator.mul,
            map(lambda (p, k): p if k else 1 - p, zip(probs, knows)),
            1)
        asked_prob += (1.0 / guess_options) * current_prob
        if guess_options > 1:
            for j in range(0, len(option_skills)):
                if knows[j + 1]:
                    continue
                opt_wrong_probs[j] += 1.0 / guess_options * current_prob
    return (asked_prob, opt_wrong_probs)


def _sigmoid(x):
    return 1.0 / (1 + exp(-x))


def _to_binary_reverse_list(number, length):
    binary = []
    for j in range(length):
        binary.append(number % 2)
        number = number / 2
    return binary
