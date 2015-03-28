# coding=utf-8
import abc
import random
import datetime
import prediction
import proso.models.metric
import pandas
import numpy


class UserKnowledgeProvider:

    @abc.abstractmethod
    def prediction(self, user, item, time, options=None):
        pass

    @abc.abstractmethod
    def process_answer(self, user, item, correct, time, response_time, options=None):
        pass

    def user_type(self, user):
        return 0

    def item_type(self, item):
        return 0

    def reset(self):
        pass


class ConstantUserKnowledgeProvider(UserKnowledgeProvider):

    def __init__(self, users, items):
        self._skill= dict([(i, random.gauss(0.5, 0.1)) for i in users])
        self._difficulty = dict([(i, random.gauss(0.5, 1.5)) for i in items])

    def prediction(self, user, item, time, options=None):
        return prediction.predict_simple(self._skill[user] - self._difficulty[item], len(options) if options else 0)[0]

    def user_type(self, user):
        skill = self._skill[user]
        percentiles = numpy.percentile(self._skill.values(), [75, 25])
        if skill > percentiles[0]:
            return 'High skill'
        elif skill < percentiles[1]:
            return 'Low skill'
        else:
            return 'Medium skill'

    def item_type(self, item):
        difficulty = self._difficulty[item]
        percentiles = numpy.percentile(self._difficulty.values(), [75, 25])
        if difficulty > percentiles[0]:
            return 'High difficulty'
        elif difficulty < percentiles[1]:
            return 'Low difficulty'
        else:
            return 'Medium difficulty'

    def process_answer(self, user, item, correct, time, response_time, options=None):
        pass


class ImprovingUserKnowledgeProvider(ConstantUserKnowledgeProvider):

    def __init__(self, users, items, time_shift=80.0, learning_good=3.4, learning_bad=0.3):
        ConstantUserKnowledgeProvider.__init__(self, users, items)
        self._current_skill = {}
        self._time_shift = time_shift
        self._learning_good = learning_good
        self._learning_bad = learning_bad
        self._last_time = {}

    def prediction(self, user, item, time, options=None):
        seconds_ago = 315460000 if self._last_time.get((user, item), None) is None else (self._last_time[user, item] - time).total_seconds()
        self._current_skill[user, item] = self._skill[user] - self._difficulty[item]
        skill = self._current_skill[user, item] + self._time_shift / seconds_ago
        if options is None:
            options = []
        if item in options:
            options.remove(item)
        options_skill = map(lambda opt: self._current_skill.get((user, opt), self._skill[user] - self._difficulty[item]), options)
        return prediction.predict(skill, options_skill)[0]

    def process_answer(self, user, item, correct, time, response_time, options=None):
        prediction = self.prediction(user, item, time, options)
        diff = self._learning_good if correct else self._learning_bad
        self._current_skill[user, item] += diff * (correct - prediction)
        self._last_time[user, item] = time

    def reset(self):
        self._current_skill = {}
        self._last_time = {}


class Activity:

    @abc.abstractmethod
    def next(self):
        pass


class OneUserActivity(Activity):

    def __init__(self, user, time_start=datetime.datetime.now()):
        self._user = user
        self._time = time_start

    def next(self):
        self._time + datetime.timedelta(seconds=10)
        return self._user, self._time


class MoreUsersActivity(Activity):

    def __init__(self, users, time_start=datetime.datetime.now()):
        self._next_user = -1
        self._users = users
        self._times = dict(zip(users, [time_start for u in users]))

    def next(self):
        self._next_user = (self._next_user + 1) % len(self._users)
        next_user = self._users[self._next_user]
        self._times[next_user] += datetime.timedelta(seconds=10)
        return next_user, self._times[next_user]


class Simulator:

    def __init__(self, users, items):
        self.users = users
        self.items = items

    def answers(self, environment, predictive_model, item_selector, n, option_selector=None):
        activity = self.activity()
        knowledge_provider = self.user_knowledge_provider()
        knowledge_provider.reset()
        answers = []
        for i in range(n):
            user, time = activity.next()
            item = item_selector.select(environment, user, self.items, time, 1)
            options = []
            if option_selector is not None:
                options = option_selector.select_options(user, item, time, self.items)
            prediction = knowledge_provider.prediction(user, item, time, options=options)
            prediction_without_options = knowledge_provider.prediction(user, item, time)
            reality = random.random()
            if reality < prediction:
                correct = True
            else:
                correct = False
            response_time = random.gauss(1000, 100)
            knowledge_provider.process_answer(user, item, correct, time, response_time, options=options)
            estimated = predictive_model.predict_and_update(environment, user, item, correct, time)
            estimated_with_options = predictive_model.predict_and_update(environment, user, item, correct, time, options=options)
            answered = item if correct else (random.choice(options) if options else None)
            if answered == item:
                correct = True
            environment.process_answer(user, item, item, answered, time, response_time)
            answers.append({
                'user': user,
                'time': time,
                'item': item,
                'options': options,
                'answered': answered,
                'correct': correct,
                'estimated': estimated_with_options,
                'estimated_without_options': estimated,
                'real_probability': prediction,
                'real_probability_without_options': prediction_without_options
            })
        return answers

    @abc.abstractmethod
    def activity(self):
        pass

    @abc.abstractmethod
    def user_knowledge_provider(self):
        pass


class OneConstantUserSimulator(Simulator):

    _activity = None
    _user_knowledge_provider = None

    def answers(self, environment, predictive_model, item_selector, n, option_selector=None):
        return Simulator.answers(self, environment, predictive_model, item_selector, n, option_selector)

    def activity(self):
        if self._activity is None:
            self._activity = OneUserActivity(self.users[0])
        return self._activity

    def user_knowledge_provider(self):
        if self._user_knowledge_provider is None:
            self._user_knowledge_provider = ConstantUserKnowledgeProvider(self.users, self.items)
        return self._user_knowledge_provider


class MoreConstantUsersSimulator(Simulator):

    _activity = None
    _user_knowledge_provider = None

    def answers(self, environment, predictive_model, item_selector, n, option_selector=None):
        return Simulator.answers(self, environment, predictive_model, item_selector, n, option_selector)

    def activity(self):
        if self._activity is None:
            self._activity = MoreUsersActivity(self.users)
        return self._activity

    def user_knowledge_provider(self):
        if self._user_knowledge_provider is None:
            self._user_knowledge_provider = ConstantUserKnowledgeProvider(self.users, self.items)
        return self._user_knowledge_provider


class MoreImprovingUsersSimulator(Simulator):

    _activity = None
    _user_knowledge_provider = None

    def answers(self, environment, predictive_model, item_selector, n, option_selector=None):
        return Simulator.answers(self, environment, predictive_model, item_selector, n, option_selector)

    def activity(self):
        if self._activity is None:
            self._activity = MoreUsersActivity(self.users)
        return self._activity

    def user_knowledge_provider(self):
        if self._user_knowledge_provider is None:
            self._user_knowledge_provider = ImprovingUserKnowledgeProvider(self.users, self.items)
        return self._user_knowledge_provider


class Evaluator:

    def __init__(self, simulator, number_of_answers=1000):
        self._simulator = simulator
        self._number_of_answers = number_of_answers

    def prepare(self, environment, predictive_model, item_selector):
        self._answers = pandas.DataFrame(self._simulator.answers(
            environment, predictive_model, item_selector, self._number_of_answers))

    def average_coverage(self):
        coverage = self._answers.groupby('user').apply(lambda data: len(data['item'].unique()) / float(len(self._simulator.items)))
        return coverage.mean(), coverage.std()

    def average_number_of_options(self):
        number_of_options = self._answers.groupby('user').apply(lambda data: data['options'].apply(len).mean())
        return number_of_options.mean(), number_of_options.std()

    def average_success(self):
        success = self._answers.groupby('user').apply(lambda data: data['correct'].sum() / float(len(data)))
        return success.mean(), success.std()

    def average_estimated(self):
        estimated = self._answers.groupby('user').apply(lambda data: data['estimated']).mean()
        return estimated.mean(), estimated.std()

    def average_estimated_without_options(self):
        estimated = self._answers.groupby('user').apply(lambda data: data['estimated_without_options']).mean()
        return estimated.mean(), estimated.std()

    def average_real_probability(self):
        real_probability = self._answers.groupby('user').apply(lambda data: data['real_probability']).mean()
        return real_probability.mean(), real_probability.std()

    def average_real_probability_without_options(self):
        real_probability = self._answers.groupby('user').apply(lambda data: data['real_probability_without_options']).mean()
        return real_probability.mean(), real_probability.std()

    def max_number_of_answers(self):
        max_number_of_answers = self._answers.groupby('user').apply(lambda data: data.groupby('item').apply(len).max())
        return max_number_of_answers.mean(), max_number_of_answers.std()

    def items_with_more_answers(self):

        def _filtered_len(data):
            items = data.groupby('item').apply(len).to_dict().items()
            items = map(lambda (i, n): i, filter(lambda (item, n): n > 1, items))
            return len(items)
        lens = self._answers.groupby('user').apply(_filtered_len)
        return lens.mean(), lens.std()

    def time_gap(self):

        def _user_time_gap(data):
            items = data.groupby('item').apply(len).to_dict().items()
            items = map(lambda (i, n): i, filter(lambda (item, n): n > 1, items))
            data = data[data['item'].isin(items)]
            return data.groupby('item').apply(lambda _data: (_data['time'] - _data['time'].shift(1)).mean())

        gaps = self._answers.groupby('user').apply(_user_time_gap)
        if len(gaps) == 0:
            return float('inf'), float('inf'), float('inf')
        stats = map(
            lambda x: x.item()if isinstance(x, pandas.Series) else x,
            [gaps.mean(), gaps.std(), gaps.min()])
        [time_mean, time_std, time_min] = map(
            lambda x: x.total_seconds() if isinstance(x, pandas.Timedelta) else x / (10.0 ** 9),
            stats)
        return time_mean, time_std, time_min

    def rmse(self):
        return proso.models.metric.rmse(self._answers['correct'], self._answers['estimated'])

    def plot_model_precision(self, environment, prediction_model, ax):
        data = []
        time = datetime.datetime(year=2100, month=1, day=1)
        number_of_answers = self._answers.groupby(['user', 'item']).apply(len).to_dict()
        success = self._answers.groupby(['user', 'item']).apply(lambda d: d['correct'].sum() / float(len(d))).to_dict()
        for item in self._simulator.items:
            for user in self._simulator.users:
                data.append({
                    'simulator': self._simulator.user_knowledge_provider().prediction(user, item, time),
                    'model': prediction_model.predict(environment, user, item, time),
                    'user_type': self._simulator.user_knowledge_provider().user_type(user),
                    'item_type': self._simulator.user_knowledge_provider().item_type(item),
                    'number_of_answers': number_of_answers.get((user, item), 0),
                    'success': success.get((user, item), None)
                })
        data = pandas.DataFrame(data)
        for group_name, group_data in data.groupby('success'):
            ax.plot(group_data['simulator'], group_data['model'], '.', color=str(max(0.1, group_name)))
        ax.set_xlabel('Simulation')
        ax.set_ylabel('Model')

    def print_stats(self, output):
        output.write('Coverage:                    {0:.2f} +/- {1:.2f}\n'.format(*self.average_coverage()))
        output.write('Number of options:           {0:.2f} +/- {1:.2f}\n'.format(*self.average_number_of_options()))
        output.write('Success per user:            {0:.2f} +/- {1:.2f}\n'.format(*self.average_success()))
        output.write('Estimated:                   {0:.2f} +/- {1:.2f}\n'.format(*self.average_estimated()))
        output.write('Estimated (without options): {0:.2f} +/- {1:.2f}\n'.format(*self.average_estimated_without_options()))
        output.write('Real prob:                   {0:.2f} +/- {1:.2f}\n'.format(*self.average_real_probability()))
        output.write('Real prob (without options): {0:.2f} +/- {1:.2f}\n'.format(*self.average_real_probability_without_options()))
        output.write('Max answers per item:        {0:.2f} +/- {1:.2f}\n'.format(*self.max_number_of_answers()))
        output.write('Items with more answers:     {0:.2f} +/- {1:.2f}\n'.format(*self.items_with_more_answers()))
        output.write('Time gap (seconds):          {0:.2f} +/- {1:.2f}, min {2:.2f}\n'.format(*self.time_gap()))
        output.write('RMSE: {0:.3f}\n'.format(self.rmse()))
