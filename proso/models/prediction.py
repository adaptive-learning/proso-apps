from functools import reduce
from math import exp
from proso.time import timeit
from proso.django.cache import cache_pure
from collections import defaultdict
import abc
import numpy
import operator


class PredictiveModel(metaclass=abc.ABCMeta):

    """
    This class handles the logic behind the predictive models, which is
    divided into 3 phases:

    * **prepare**: the model loads the necessary data from the environment
    * **predict**: the model uses the loaded data to predict the correctness of the answer
    * **update**: the model updates environment to persist it for the future prediction
    """

    @timeit(name='prediction')
    def predict_more_items(self, environment, user, items, time, **kwargs):
        data = self.prepare_phase_more_items(environment, user, items, time, **kwargs)
        return self.predict_phase_more_items(data, user, items, time, **kwargs)

    def predict(self, environment, user, item, time, **kwargs):
        data = self.prepare_phase(environment, user, item, time, **kwargs)
        return self.predict_phase(data, user, item, time, **kwargs)

    def predict_and_update(self, environment, user, item, correct, time, answer_id, **kwargs):
        data = self.prepare_phase(environment, user, item, time, **kwargs)
        prediction = self.predict_phase(data, user, item, time, **kwargs)
        self.update_phase(
            environment, data, prediction, user, item, correct, time, answer_id, **kwargs)
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
    def update_phase(self, environment, data, prediction, user, item, correct, time, answer_id, **kwargs):
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

    def update_phase(self, environment, data, prediction, user, item, correct, time, answer_id, **kwargs):
        self.simple_update(prediction, user, item, correct, time, answer_id, **kwargs)

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
        total_sums, number_of_answers = data
        return [total_sums[i] / max(number_of_answers[i], 1) for i in items]

    def update_phase(self, environment, data, prediction, user, item, correct, time, answer_id, **kwargs):
        environment.update('total_sum', 0, lambda x: x + correct, item=item, answer=answer_id)


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
            seconds_ago = _total_seconds_diff(time, data['last_time']) if data['last_time'] and time else 315460000
            skill = data['current_skill'] + self._time_shift / max(seconds_ago, 0.001)
        return predict_simple(
            skill,
            number_of_options=len(kwargs['options']) if 'options' in kwargs else 0,
            guess=kwargs.get('guess'))[0]

    def predict_phase_more_items(self, data, user, items, time, **kwargs):
        preds = []
        for i in items:
            preds.append(self.predict_phase({
                'prior_skill': data['prior_skill'],
                'difficulty': data['difficulties'][i],
                'current_skill': data['current_skills'][i],
                'last_time': data['last_times'][i],
            }, user, i, time, **kwargs))
        return preds

    def update_phase(self, environment, data, prediction, user, item, correct, time, answer_id, **kwargs):
        result = correct
        if data['current_skill'] is None:
            current_skill = data['prior_skill'] - data['difficulty']
        else:
            current_skill = data['current_skill']
        if result:
            current_skill = current_skill + self._pfae_good * (result - prediction)
        else:
            current_skill = current_skill + self._pfae_bad * (result - prediction)
        environment.write('current_skill', current_skill, user=user, item=item, time=time, answer=answer_id)
        if data['use_prior']:
            alpha_fun = lambda n: self._elo_alpha / (1 + self._elo_dynamic_alpha * n)
            prior_skill_alpha = alpha_fun(data['user_first_answers'])
            difficulty_alpha = alpha_fun(data['item_first_answers'])
            environment.write(
                'prior_skill', data['prior_skill'] + prior_skill_alpha * (result - prediction),
                user=user, time=time, answer=answer_id)
            environment.write(
                'difficulty', data['difficulty'] - difficulty_alpha * (result - prediction),
                item=item, time=time, answer=answer_id)


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
        all_items = list(set(items + [i for ps in list(parents.values()) for (i, v) in ps]))
        return {
            'skills': environment.read_more_items('skill', items=all_items, user=user, default=0),
            'first_answers': environment.number_of_first_answers_more_items(items=items),
            'difficulties': environment.read_more_items('difficulty', items=items, default=0),
            'last_times': environment.last_answer_time_more_items(items=items, user=user),
            'parents': parents,
        }

    def predict_phase(self, data, user, item, time, **kwargs):
        skill = self._load_skill(item, data)
        difficulty = data['difficulties'][item]
        return predict_simple(
            skill - difficulty,
            number_of_options=len(kwargs['options']) if 'options' in kwargs else 0,
            guess=kwargs.get('guess'))[0]

    def predict_phase_more_items(self, data, user, items, time, **kwargs):
        return [self.predict_phase(data, user, i, time, **kwargs) for i in items]

    def update_phase(self, environment, data, prediction, user, item, correct, time, answer_id, **kwargs):
        if data['last_times'][item] is None:
            alpha_fun = lambda n: self._elo_alpha / (1 + self._elo_dynamic_alpha * n)
            difficulty_alpha = alpha_fun(data['first_answers'][item])
            data['difficulties'][item] -= difficulty_alpha * (correct - prediction)
            environment.write('difficulty', data['difficulties'][item], item=item, time=time, answer=answer_id)
        parents_per_level = [
            list(set([i_w[0] for i_w in parents])) for parents in self._iterate_parents_per_level(item, data)]
        parents_per_level = list(zip(list(range(len(parents_per_level))), parents_per_level))
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
                environment.write('skill', data['skills'][parent], item=parent, user=user, time=time, answer=answer_id)

    def _load_parents(self, environment, items, user):
        parents = {}
        while len(items) > 0:
            found = environment.get_items_with_values_more_items('parent', items)
            new_items = set()
            for i, ps in found.items():
                new_items = new_items.union([x[0] for x in ps])
                if len(ps) == 0:
                    ps.append((None, 1))
                parents[i] = ps
            items = list(new_items)
        return parents

    def _load_skill(self, item, data):
        skill = 0
        for skill_items in self._iterate_parents_per_level(item, data):
            weights = float(sum([i_w1[1] for i_w1 in skill_items]))
            skill += sum([data['skills'][i_w3[0]] * i_w3[1] / weights for i_w3 in skill_items])
        return skill

    def _iterate_parents_per_level(self, item, data):
        to_find = [(item, 1)]
        while len(to_find) > 0:
            yield to_find
            to_find = [iw for ps in [[] if i_w2[0] is None else data['parents'][i_w2[0]] for i_w2 in to_find] for iw in ps]


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

    def update_phase(self, environment, data, prediction, user, item, correct, time, answer_id, **kwargs):
        return super(ShiftedPredictiveModel, self).update_phase(
            environment, data, prediction, user, item, correct, time, answer_id, **kwargs)

    def predict_and_update(self, environment, user, item, correct, time, **kwargs):
        return super(ShiftedPredictiveModel, self).predict_and_update(environment, user, item, correct, time, **kwargs)

    def predict_more_items(self, environment, user, items, time, **kwargs):
        return [min(1.0, max(0.0, p + self._prediction_shift)) for p in super(ShiftedPredictiveModel, self).predict_more_items(environment, user, items, time, **kwargs)]


class PFAEStaircase(PredictiveModel):

    def __init__(self, pfae_good=1.8, pfae_bad=0.8, elo_alpha=0.8, elo_dynamic_alpha=0.05, staircase_size=20, staircase_base=60, parent_contribution=0.3):
        self._pfae_good = pfae_good
        self._pfae_bad = pfae_bad
        self._elo_alpha = elo_alpha
        self._elo_dynamic_alpha = elo_dynamic_alpha
        self._staircase = [0] + [staircase_base * 2 ** i for i in range(staircase_size)]
        MAX = 10 * 365 * 24 * 60 * 60  # 10 years
        if MAX > self._staircase[-1]:
            self._staircase.append(MAX)
        self._parent_contribution = parent_contribution

    def prepare_phase(self, environment, user, item, time, **kwargs):
        result = {}
        result['parents'], parent_ids = self._load_structure_for_items(environment, [item])
        result['parents'] = result['parents'][item]
        parent_ids = list(parent_ids)
        result['prior_skill'] = environment.read('prior_skill', user=user, default=0)
        result['difficulties'] = environment.read_more_items('difficulty', items=[item] + parent_ids, default=0)
        result['parent_updates'] = environment.read_more_items('number_of_difficulty_updates', items=parent_ids, default=0)
        result['current_skill'] = environment.read('current_skill', user=user, item=item)
        result['use_prior'] = result['current_skill'] is None
        if result['use_prior']:
            result['user_first_answers'] = environment.number_of_first_answers(user=user)
            result['item_first_answers'] = environment.number_of_first_answers(item=item)
        else:
            result['last_time'] = environment.last_answer_time(user=user, item=item)
            staircase_keys = ['staircase_val_{}'.format(i) for i in self._staircase] + ['staircase_count_{}'.format(i) for i in self._staircase]
            staircase_loaded = environment.read_more_keys(staircase_keys, default=0)
            result['staircase'] = {
                s: (staircase_loaded['staircase_val_{}'.format(s)], staircase_loaded['staircase_count_{}'.format(s)])
                for s in self._staircase
            }
        return result

    def prepare_phase_more_items(self, environment, user, items, time, **kwargs):
        result = {}
        result['parents'], parent_ids = self._load_structure_for_items(environment, items)
        parent_ids = list(parent_ids)
        result['prior_skill'] = environment.read('prior_skill', user=user, default=0)
        result['difficulties'] = environment.read_more_items('difficulty', items=items + parent_ids, default=0)
        result['current_skills'] = environment.read_more_items('current_skill', user=user, items=items)
        result['last_times'] = environment.last_answer_time_more_items(user=user, items=items)
        result['items_has_answer'] = environment.has_answer_more_items(items=items)
        staircase_keys = ['staircase_val_{}'.format(i) for i in self._staircase] + ['staircase_count_{}'.format(i) for i in self._staircase]
        staircase_loaded = environment.read_more_keys(staircase_keys, default=0)
        result['staircase'] = {
            s: (staircase_loaded['staircase_val_{}'.format(s)], staircase_loaded['staircase_count_{}'.format(s)])
            for s in self._staircase
        }
        return result

    def predict_phase(self, data, user, item, time, **kwargs):
        if data['current_skill'] is None:
            if len(data['parents']) > 0:
                total_parent_weight = sum(data['parents'].values())
                parent_difficulty = sum([data['difficulties'][p] * w for p, w in data['parents'].items()]) / total_parent_weight
                if ('item_first_answers' in data and data['item_first_answers'] == 0) or ('item_has_answer' in data and data['item_has_answer']):
                    total_difficulty = parent_difficulty
                else:
                    total_difficulty = (1 - self._parent_contribution) * data['difficulties'][item] + self._parent_contribution * parent_difficulty
                skill = data['prior_skill'] - total_difficulty
            else:
                skill = data['prior_skill'] - data['difficulties'][item]
        else:
            seconds_ago = _total_seconds_diff(time, data['last_time']) if data['last_time'] and time else self._staircase[-1]
            skill = data['current_skill'] + self._get_shift(seconds_ago, data['staircase'])
        return predict_simple(
            skill,
            number_of_options=len(kwargs['options']) if 'options' in kwargs else 0,
            guess=kwargs.get('guess'))[0]

    def predict_phase_more_items(self, data, user, items, time, **kwargs):
        preds = []
        for i in items:
            preds.append(self.predict_phase({
                'prior_skill': data['prior_skill'],
                'difficulties': data['difficulties'],
                'current_skill': data['current_skills'][i],
                'last_time': data['last_times'][i],
                'item_has_answer': data['items_has_answer'][i],
                'staircase': data['staircase'],
                'parents': data['parents'][i],
            }, user, i, time, **kwargs))
        return preds

    def update_phase(self, environment, data, prediction, user, item, correct, time, answer_id, **kwargs):
        result = correct
        diff = result - prediction
        if data['current_skill'] is None:
            if len(data['parents']) > 0:
                total_parent_weight = sum(data['parents'].values())
                parent_difficulty = sum([data['difficulties'][p] * w for p, w in data['parents'].items()]) / total_parent_weight
                if data['item_first_answers'] == 0:
                    total_difficulty = parent_difficulty
                else:
                    total_difficulty = (1 - self._parent_contribution) * data['difficulties'][item] + self._parent_contribution * parent_difficulty
                current_skill = data['prior_skill'] - total_difficulty
            else:
                current_skill = data['prior_skill'] - data['difficulties'][item]
        else:
            current_skill = data['current_skill']
        if result:
            current_skill = current_skill + self._pfae_good * diff
        else:
            current_skill = current_skill + self._pfae_bad * diff
        environment.write('current_skill', current_skill, user=user, item=item, time=time, answer=answer_id)
        if data['use_prior']:
            alpha_fun = lambda n: self._elo_alpha / (1 + self._elo_dynamic_alpha * n)
            prior_skill_alpha = alpha_fun(data['user_first_answers'])
            difficulty_alpha = alpha_fun(data['item_first_answers'])
            environment.write(
                'prior_skill', data['prior_skill'] + prior_skill_alpha * diff,
                user=user, time=time, answer=answer_id)
            environment.write(
                'difficulty', data['difficulties'][item] - difficulty_alpha * diff,
                item=item, time=time, answer=answer_id)
            for parent in data['parents']:
                updates = data['parent_updates'][parent]
                environment.write(
                    'difficulty', data['difficulties'][parent] - alpha_fun(updates) * diff,
                    item=parent, time=time, answer=answer_id, audit=False)
                environment.update('number_of_difficulty_updates', 0, lambda x: x + 1, item=parent)

        else:
            seconds_ago = _total_seconds_diff(time, data['last_time']) if data['last_time'] and time else self._staircase[-1]
            self._update_shift(environment, seconds_ago, data['staircase'], diff)

    def _update_shift(self, environment, seconds_ago, staircase, diff):
        lower, upper, distance = self._get_staircase_bucket(seconds_ago)
        stored_lower = staircase[lower]
        stored_upper = staircase[upper]
        if stored_lower is None:
            stored_lower = (0, 0)
        if stored_upper is None:
            stored_upper = (0, 0)
        environment.write(
            'staircase_val_{}'.format(lower),
            stored_lower[0] + diff * (1 - distance)
        )
        environment.write(
            'staircase_count_{}'.format(lower),
            stored_lower[1] + 1 - distance
        )
        environment.write(
            'staircase_val_{}'.format(upper),
            stored_upper[0] + diff * distance
        )
        environment.write(
            'staircase_count_{}'.format(upper),
            stored_upper[1] + distance
        )

    def _get_shift(self, seconds_ago, staircase):
        lower, upper, distance = self._get_staircase_bucket(seconds_ago)
        stored_lower = staircase[lower]
        stored_upper = staircase[upper]
        if stored_lower is None:
            stored_lower = (0, 0)
        if stored_upper is None:
            stored_upper = (0, 0)
        return numpy.round(
            (1 - distance) * (0 if stored_lower[1] == 0 else stored_lower[0] / stored_lower[1])
            +
            distance * (0 if stored_upper[1] == 0 else stored_upper[0] / stored_upper[1]),
            4)

    def _get_staircase_bucket(self, seconds_ago):
        seconds_ago = max(0.01, min(self._staircase[-1] - 1, seconds_ago))
        lower = max([mod for mod in self._staircase if mod <= seconds_ago])
        upper = min([mod for mod in self._staircase if mod > seconds_ago])
        seconds_ago_log = numpy.log(seconds_ago)
        lower_log = numpy.log(lower) if lower > 1 else 0
        upper_log = numpy.log(upper)
        distance = (seconds_ago_log - lower_log) / (upper_log - lower_log)
        return lower, upper, distance

    def _load_structure_for_items(self, environment, item_ids):
        parents = {}
        parent_ids = set()
        for item_id in item_ids:
            item_parents = self._load_parents(environment, item_id)
            parents[item_id] = item_parents
            parent_ids |= set(item_parents.keys())
        return parents, list(parent_ids)

    def _load_children(self, environment, item_id):
        return self._get_structure(environment)[1].get(item_id, {})

    def _load_parents(self, environment, item_id):
        return self._get_structure(environment)[0].get(item_id, {})

    def _get_structure(self, environment):
        if not hasattr(self, '_structure'):
            self._structure = self._prepare_structure(environment)
        return self._structure

    @cache_pure()
    def _prepare_structure(self, environment):
        parents = defaultdict(lambda: [])
        children = defaultdict(lambda: [])
        for _, child, parent, value in environment.read_all_with_key('parent'):
            parents[child].append((parent, value))
            children[parent].append((child, value))
        parents = {c: {p: 1 / (len(children[p]) + 1) for p, _ in ps} for c, ps in parents.items()}
        children = {p: {c: 1 / (len(parents[c]) + 1) for c, _ in cs} for p, cs in children.items()}
        return parents, children


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

    probs = [_sigmoid(x) for x in [skill_asked] + option_skills]
    items = 2 ** len(probs)
    asked_prob = 0
    opt_wrong_probs = [0 for i in option_skills]

    for i in range(items):
        knows = _to_binary_reverse_list(i, len(probs))
        guess_options = 1 if knows[0] else sum([1 - x for x in knows])
        current_prob = reduce(
            operator.mul,
            [p_k[0] if p_k[1] else 1 - p_k[0] for p_k in zip(probs, knows)],
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


def _total_seconds_diff(a, b):
    if a.tzinfo != b.tzinfo:
        a = a if a.tzinfo is None else a.replace(tzinfo=None)
        b = b if b.tzinfo is None else b.replace(tzinfo=None)
    return (a - b).total_seconds()
