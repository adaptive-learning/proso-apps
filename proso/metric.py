import numpy


def binomial_confidence_mean(xs, z=1.96):
    if len(xs) == 0:
        return None, (None, None)
    mean = numpy.mean(xs)
    confidence = z * numpy.sqrt((mean * (1 - mean)) / len(xs))
    return mean, (mean - confidence, mean + confidence)


def confidence_median(xs, z=1.96):
    # see https://epilab.ich.ucl.ac.uk/coursematerial/statistics/non_parametric/confidence_interval.html
    xs.sort()
    mod = ((z * numpy.sqrt(len(xs))) / 2.0)
    lower = max(0, int(numpy.round(len(xs) / 2.0 - mod)) - 1)
    upper = min(len(xs) - 1, int(numpy.round(1 + len(xs) / 2.0 + mod)) - 1)
    return numpy.median(xs), (xs[lower], xs[upper])


def confidence_value_to_json(confidence_value):
    return {
        'value': None if confidence_value[0] is None else format_number(confidence_value[0]),
        'confidence_interval': {
            'min': None if confidence_value[0] is None else format_number(confidence_value[1][0]),
            'max': None if confidence_value[0] is None else format_number(confidence_value[1][1]),
        }
    }


def format_number(x):
    return float('{0:.2f}'.format(x))
