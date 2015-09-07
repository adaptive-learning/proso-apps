import proso.models.option_selection
import random


class TestNonOptionSelection(proso.models.option_selection.TestOptionSelection):

    def get_option_selector(self, item_selector):
        return proso.models.option_selection.NonOptionSelection(item_selector)


class TestRandomOptionSelection(proso.models.option_selection.TestOptionSelection):

    def get_option_selector(self, item_selector):
        random.seed(2)
        return proso.models.option_selection.RandomOptionSelection(item_selector)


class TestConfusingOptionSelection(proso.models.option_selection.TestOptionSelection):

    def get_option_selector(self, item_selector):
        return proso.models.option_selection.ConfusingOptionSelection(item_selector)
