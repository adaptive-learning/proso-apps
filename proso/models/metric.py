from sklearn.metrics import roc_curve, auc as sk_auc
import math
import scipy as sp
import numpy as np


def auc(expected, found):
    fpr, tpr, thresholds = roc_curve(expected, found)
    return sk_auc(fpr, tpr)


def logloss(expected, found):
    _same_lengths(expected, found)
    epsilon = 1e-15
    found = sp.minimum(1 - epsilon, sp.maximum(epsilon, found))
    ll = sum(expected * sp.log(found) + sp.subtract(1, expected) * sp.log(sp.subtract(1, found)))
    return ll * -1.0 / len(expected)


def mae(expected, found):
    _same_lengths(expected, found)
    return np.mean(np.absolute(np.array(expected) - np.array(found)))


def rmse(expected, found):
    _same_lengths(expected, found)
    return math.sqrt(np.mean((np.array(expected) - np.array(found)) ** 2))


def _same_lengths(*args):
    last_length = -1
    for arg in args:
        if last_length != -1 and last_length != len(arg):
            raise Exception('arguments differ in length')
        last_length = len(arg)
