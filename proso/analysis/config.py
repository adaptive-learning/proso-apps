from threading import currentThread
import seaborn as sns
import argparse

sns.set_style(style='white')


DATA_KWARGS_KEYS = ['data_dir', 'answer_limit', 'language']
OUTPUT_KWARGS_KEYS = ['output_dir', 'figure_extension']
CACHE_KWARGS_KEYS = ['cache_dir', 'is_cache_active', 'override_cache', 'cache_in_memory']

_sns_palette = {}
_data_kwargs = {}
_cache_kwargs = {}
_output_kwargs = {}


def get_argument_parser():
    p = argparse.ArgumentParser()

    p.add_argument(
        "-d",
        "--data",
        action="store",
        dest="data_dir",
        default='data'
    )
    p.add_argument(
        "--lang",
        action='store',
        dest='language',
        default='en'
    )
    p.add_argument(
        '-l',
        '--answer-limit',
        action='store',
        dest='answer_limit',
        default=1
    )
    p.add_argument(
        '-o',
        '--output',
        action='store',
        dest='output_dir',
        default='output'
    )
    p.add_argument(
        '-e',
        '--extension',
        action='store',
        dest='figure_extension',
        default='png'
    )
    p.add_argument(
        '-p',
        '--palette',
        action='store',
        default=None
    )
    p.add_argument(
        '-c',
        '--cache-dir',
        action='store',
        dest='cache_dir',
        default='cache'
    )
    p.add_argument(
        '--disable-cache',
        action='store_false',
        dest='is_cache_active',
        default=True)
    p.add_argument(
        '--disable-cache-in-memory',
        action='store_false',
        dest='cache_in_memory',
        default=True)
    p.add_argument(
        '--override-cache',
        action='store_true',
        dest='override_cache',
        default=False)
    return p


def init_data_kwargs(parsed_kwargs):
    data_kwargs = {}
    for kwarg_key in DATA_KWARGS_KEYS:
        data_kwargs[kwarg_key] = parsed_kwargs[kwarg_key]
        del parsed_kwargs[kwarg_key]
    store_data_kwargs(**data_kwargs)


def init_cache_kwargs(parsed_kwargs):
    cache_kwargs = {}
    for kwarg_key in CACHE_KWARGS_KEYS:
        cache_kwargs[kwarg_key] = parsed_kwargs[kwarg_key]
        del parsed_kwargs[kwarg_key]
    store_cache_kwargs(**cache_kwargs)


def init_output_kwargs(parsed_kwargs):
    output_kwargs = {}
    for kwarg_key in OUTPUT_KWARGS_KEYS:
        output_kwargs[kwarg_key] = parsed_kwargs[kwarg_key]
        del parsed_kwargs[kwarg_key]
    store_output_kwargs(**output_kwargs)
    if parsed_kwargs.get('palette') is not None:
        store_palette(palette_name=parsed_kwargs['palette'])
    if 'palette' in parsed_kwargs:
        del parsed_kwargs['palette']


def process_kwargs(parsed_kwargs):
    return {key: _convert_kwarg_value(val) for (key, val) in parsed_kwargs.items()}


def store_data_kwargs(**kwargs):
    global _data_kwargs
    _data_kwargs[currentThread()] = kwargs


def load_data_kwargs():
    global _data_kwargs
    return _data_kwargs[currentThread()]


def store_cache_kwargs(**kwargs):
    global _cache_kwargs
    _cache_kwargs[currentThread()] = kwargs


def load_cache_kwargs():
    global _cache_kwargs
    return _cache_kwargs[currentThread()]


def store_palette(palette=None, palette_name=None):
    if palette is None and palette_name is None:
        raise Exception('Either palette itself, or palette name has to be given.')
    if palette is not None and palette_name is not None:
        raise Exception('Both palette itself or palette name can not be given.')
    global _sns_palette
    if palette is not None:
        _sns_palette[currentThread()] = palette
    else:
        _sns_palette[currentThread()] = sns.color_palette(palette_name)
    sns.set_palette(_sns_palette[currentThread()])


def load_palette():
    global _sns_palette
    return _sns_palette.get(currentThread(), sns.color_palette())


def store_output_kwargs(**kwargs):
    global _output_kwargs
    _output_kwargs[currentThread()] = kwargs


def load_output_kwargs():
    global _output_kwargs
    return _output_kwargs[currentThread()]


def _convert_kwarg_value(val):
    if not isinstance(val, str):
        return val
    if val == 'False':
        return False
    elif val == 'True':
        return True
    else:
        try:
            return int(val)
        except ValueError:
            pass
        try:
            return float(val)
        except ValueError:
            return val
    return val


