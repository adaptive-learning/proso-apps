import json
import hashlib
import os


def get_experiment_data(name, compute_fun, cache_dir, cached=True, **kwargs):
    kwargs_hash = hashlib.sha1(json.dumps(kwargs, sort_keys=True)).hexdigest()
    filename = '{}/{}.json'.format(cache_dir, name);
    if cached and os.path.exists(filename):
        with open(filename, 'r') as f:
            return _convert_json_keys(json.loads(f.read()))
    result = compute_fun(**kwargs)
    if cached:
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        with open(filename, 'w') as f:
            f.write(json.dumps(result, sort_keys=True))
    return result


def _convert_json_keys(json_struct):
    if isinstance(json_struct, list):
        return map(_convert_json_keys, json_struct)
    elif isinstance(json_struct, dict):
        return {_maybe_convert_str(key): val for (key, val) in json_struct.iteritems()}
    else:
        return json_struct


def _maybe_convert_str(x):
    if x.isdigit():
        try:
            return int(x)
        except ValueError:
            pass
    try:
        return float(x)
    except ValueError:
        return x

