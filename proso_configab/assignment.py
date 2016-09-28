from proso.rand import roulette
import abc
import random


class Strategy(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def assign_setups(self, user_id, setups_by_experiment):
        pass


class RandomStrategy(Strategy):

    def assign_setups(self, user_id, setups_by_experiment):
        random.seed(user_id)
        result = []
        for experiment_id, setups in setups_by_experiment.items():
            chosen_id = roulette({s.id: s.probability for s in setups}, 1)[0]
            chosen_setup = [s for s in setups if s.id == chosen_id][0]
            result.append(chosen_setup)
        return result
