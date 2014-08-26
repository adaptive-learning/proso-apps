import abc


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

    def predict_more_items(self, environment, user, items, asked_items, time, **kwargs):
        data = self.prepare_phase_more_items(environment, user, items, asked_items, time, **kwargs)
        return self.predict_phase_more_items(data, user, items, asked_items, time, **kwargs)

    def predict(self, environment, user, item, asked, time, **kwargs):
        data = self.prepare_phase(environment, user, item, asked, time, **kwargs)
        return self.predict_phase(data, user, item, asked, time, **kwargs)

    def predict_and_update(self, environment, user, item, asked, answered, time, **kwargs):
        data = self.prepare_phase(environment, user, item, asked, time, **kwargs)
        prediction = self.predict_phase(data, user, item, asked, time, **kwargs)
        self.update_phase(
            environment, data, prediction, user, item, asked, answered, time, **kwargs)
        return prediction

    @abc.abstractmethod
    def prepare_phase(self, environment, user, item, asked, time, **kwargs):
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
            asked (int):
                identifier of the asked item
            time (datetime.datetime):
                datetime when the question is asked
            kwargs:
                used for other information about the question

        Returns:
            object
        """
        pass

    @abc.abstractmethod
    def prepare_phase_more_items(self, environment, user, items, asked_items, time, **kwargs):
        pass

    @abc.abstractmethod
    def predict_phase(self, data, user, item, asked, time, **kwargs):
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
            asked (int):
                identifier of the asked item
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
    def predict_phase_more_items(self, data, user, item, asked, time, **kwargs):
        pass

    @abc.abstractmethod
    def update_phase(self, environment, data, prediction, user, item, asked, answered, time, **kwargs):
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
            asked (int):
                identifier of the asked item
            answered (int):
                identifier of the asked item
            time (datetime.datetime):
                datetime when the question is asked
            kwargs:
                used for other information about the question and the answer
        """
        pass


class AveragePredictiveModel(PredictiveModel):

    def prepare_phase(self, environment, user, item, asked, time, **kwargs):
        total_sum = environment.read('total_sum', item=item, default=0)
        number_of_answers = environment.number_of_answers(item=item)
        return total_sum, number_of_answers

    def prepare_phase_more_items(self, environment, user, items, asked_items, time, **kwargs):
        total_sums = environment.read_more_items('total_sum', items=items, default=0)
        number_of_answers = environment.number_of_answers_more_items(items=items)
        return total_sums, number_of_answers

    def predict_phase(self, data, user, item, asked, time, **kwargs):
        return float(data[0]) / max(data[1], 1)

    def predict_phase_more_items(self, data, user, items, asked_items, time, **kwargs):
        return map(lambda (tot, num): float(tot) / max(num, 1), zip(data[0], data[1]))

    def update_phase(self, environment, data, prediction, user, item, asked, answered, time, **kwargs):
        environment.update('total_sum', 0, lambda x: x + (asked == answered), item=item)
