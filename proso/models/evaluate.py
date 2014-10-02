import proso.geography.dfutil
import numpy as np
import metric
from clint.textui import progress


class Evaluator:

    def __init__(self, answers, predictive_model, environment=None):
        self._predictive_model = predictive_model
        self._environment = environment
        self._answers = answers
        self._prediction = []
        self._correctness = []

    def prepare(self, stdout=False):
        iterator = proso.geography.dfutil.iterdicts(self._answers)
        if stdout:
            iterator = progress.bar(iterator, every=len(self._answers) / 100)
        for answer in iterator:
            pred = self._predictive_model.predict_and_update(
                self._environment,
                answer['user'],
                answer['place_asked'],
                answer['place_asked'] == answer['place_answered'],
                answer['inserted'],
                response_time=answer['response_time'],
                options=answer['options'])
            if self._environment is not None:
                self._environment.process_answer(
                    answer['user'],
                    answer['place_asked'],
                    answer['place_asked'],
                    answer['place_answered'],
                    answer['inserted'],
                    answer['response_time'],
                    options=answer['options'])
            if isinstance(pred, tuple):
                pred = pred[0]
            if pred < 0 or pred > 1:
                Exception('The prediction is out of the range [0, 1]: ' + str(pred))
            self._prediction.append(pred)
            self._correctness.append(answer['place_asked'] == answer['place_answered'])

    def auc(self):
        return metric.auc(self._correctness, self._prediction)

    def brier(self, bins=10):
        """
        Compute Brier score

        Args:
            bins (int): number of bins
        Return:
            float, float, float: reliability, resolution, uncertainty
        """
        bin_correctness, bin_prediction, bin_count = self._bin_stats(bins=bins)
        rel, res = 0, 0
        size = float(len(self._correctness))
        mean_correct_total = sum(self._correctness) / size
        for corr, pred, count in zip(bin_correctness, bin_prediction, bin_count):
            rel += count * (pred - corr) ** 2
            res += count * (pred - mean_correct_total) ** 2
        return rel / size, res / size, mean_correct_total * (1 - mean_correct_total)

    def calibration_graphs(self, fig, bins=10):
        bin_correctness, bin_prediction, bin_count = self._bin_stats(bins=bins)
        ax = fig.add_subplot(211)
        ax.plot(bin_correctness, bin_prediction, color='blue', label='Prediction')
        ax.set_xlabel('Average correctness')
        ax.set_ylabel('Average prediction')
        ax.set_xlim(0, 1)
        ax.plot((0, 1), (0, 1), color='red', label='Optimal')
        ax.legend(loc='upper left')
        ax = fig.add_subplot(212)
        ax.hist(self._prediction)
        ax.set_xlabel('Prediction')
        ax.set_xlim(0, 1)
        ax.set_ylabel('Number of answers')

    def logloss(self):
        return metric.logloss(self._correctness, self._prediction)

    def rmse(self):
        return metric.rmse(self._correctness, self._prediction)

    def _bin_stats(self, bins=10):
        """
        Divide answer to the given number of bins according to the prediction
        and compute the average correctness and prediction for each bin.

        Args:
            bins (int): number of bins
        Return:
            numpy.Array, numpy.Array, numpy.Array:
                average correctness, avarage prediction divided to the given number
                of bins and number of answers for each bin
        """
        sum_answer = np.zeros(bins)  # sum of correctness in the given bin
        sum_pred = np.zeros(bins)  # sum of probabilities in the given bin
        count = np.zeros(bins)  # number of answers in the given bin
        for pred, answer in zip(self._prediction, self._correctness):
            b = min(bins - 1, int(pred * bins))  # find bin
            sum_answer[b] += answer
            sum_pred[b] += pred
            count[b] += 1
        freq = np.zeros(bins)  # ratio of the correct answers in the given bin
        bin_mean = np.zeros(bins)  # mean prediction for the given bin
        for i in range(bins):
            if count[i]:
                freq[i] = sum_answer[i] / count[i]
                bin_mean[i] = sum_pred[i] / count[i]
            else:
                bin_mean[i] = (i + 0.5) * 1.0 / bins
        return bin_mean, freq, count
