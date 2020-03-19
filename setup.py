from setuptools import setup
import os
import proso.release

DIR = os.path.dirname(os.path.abspath(__file__))
VERSION = proso.release.VERSION


def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [
        line
        for line in lineiter
        if line and not line.startswith("#") and not line.startswith('git+')
    ]


setup(
    name='proso-apps',
    version=VERSION,
    description='General library for applications in PROSO projects',
    author='Adaptive Learning Group',
    author_email='al@fi.muni.cz',
    url='https://github.com/adaptive-learning/proso-apps',
    namespace_packages=['proso', 'proso.django'],
    include_package_data=True,
    packages=[
        'proso',
        'proso.django',
        'proso.models',
        'proso_common',
        'proso_common.management',
        'proso_common.management.commands',
        'proso_common.migrations',
        'proso_concepts',
        'proso_concepts.management',
        'proso_concepts.management.commands',
        'proso_concepts.migrations',
        'proso_configab',
        'proso_configab.management',
        'proso_configab.management.commands',
        'proso_configab.migrations',
        'proso_feedback',
        'proso_feedback.migrations',
        'proso_flashcards',
        'proso_flashcards.management',
        'proso_flashcards.management.commands',
        'proso_flashcards.migrations',
        'proso_models',
        'proso_models.management',
        'proso_models.management.commands',
        'proso_models.migrations',
        'proso_subscription',
        'proso_subscription.management',
        'proso_subscription.management.commands',
        'proso_subscription.migrations',
        'proso_tasks',
        'proso_tasks.management',
        'proso_tasks.management.commands',
        'proso_tasks.migrations',
        'proso_user',
        'proso_user.management',
        'proso_user.management.commands',
        'proso_user.migrations',
    ],
    setup_requires=[
        'Sphinx>=1.3',
        'sphinxcontrib-napoleon>=0.5.0',
    ],
    install_requires=parse_requirements(DIR + '/docs/requirements.txt') + [
        'ipython',
        'numpy',
    ],
    license='MIT',
)
