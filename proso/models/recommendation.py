import abc
import random


class Recommendation:

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def recommend(self, environment, user, items, n):
        pass


class RandomRecommendation(Recommendation):

    def recommend(self, environment, user, items, n):
        return random.sample(items, n)
