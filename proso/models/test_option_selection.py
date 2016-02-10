import proso.models.option_selection
import random


class TestFullyRandomOptionsNumber(proso.models.option_selection.TestOptionsNumber):

    def get_options_number(self, max_options, allow_zero_options_restriction):
        return proso.models.option_selection.FullyRandomOptionsNumber(
            max_options=max_options,
            allow_zero_options_restriction=allow_zero_options_restriction
        )


class TestPartiallyRandomNumber(proso.models.option_selection.TestOptionsNumber):

    def get_options_number(self, max_options, allow_zero_options_restriction):
        return proso.models.option_selection.PartiallyRandomOptionsNumber(
            max_options=max_options,
            allow_zero_options_restriction=allow_zero_options_restriction
        )


class TestAdjustedOptionsNumber(proso.models.option_selection.TestOptionsNumber):

    def get_options_number(self, max_options, allow_zero_options_restriction):
        return proso.models.option_selection.AdjustedOptionsNumber(
            max_options=max_options,
            allow_zero_options_restriction=allow_zero_options_restriction
        )


class TestUniformlyAdjustedOptionsNumber(proso.models.option_selection.TestOptionsNumber):

    def get_options_number(self, max_options, allow_zero_options_restriction):
        return proso.models.option_selection.UniformlyAdjustedOptionsNumber(
            max_options=max_options,
            allow_zero_options_restriction=allow_zero_options_restriction
        )


class TestRandomOptionSelection(proso.models.option_selection.TestOptionSelection):

    def get_option_selector(self, item_selector, options_number):
        random.seed(2)
        return proso.models.option_selection.RandomOptionSelection(item_selector, options_number)


class TestCompetitiveOptionSelection(proso.models.option_selection.TestOptionSelection):

    def get_option_selector(self, item_selector, options_number):
        return proso.models.option_selection.CompetitiveOptionSelection(item_selector, options_number)


class TestAdjustedOptionSelection(proso.models.option_selection.TestOptionSelection):

    def get_option_selector(self, item_selector, options_number):
        return proso.models.option_selection.AdjustedOptionSelection(item_selector, options_number)
