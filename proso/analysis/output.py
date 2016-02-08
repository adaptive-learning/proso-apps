import proso.analysis.config
import proso.analysis.utils
import os.path
import matplotlib.pyplot as plt


def savefig(filename):
    _savefig(filename, **proso.analysis.config.load_output_kwargs())


def _savefig(filename, output_dir, figure_extension, **kwargs):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    plt.tight_layout()
    filename = '{}/{}.{}'.format(output_dir, filename, figure_extension)
    plt.savefig(filename)
    proso.analysis.utils.info(filename)
