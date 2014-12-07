from setuptools import setup, find_packages
import os

VERSION = '0.9.0'

setup(
    name='proso-apps',
    version=VERSION,
    description='General library for applications in PROSO projects',
    author='Jan Papousek, Vit Stanislav',
    author_email='jan.papousek@gmail.com, slaweet@seznam.cz',
    namespace_packages = ['proso', 'proso.django'],
    include_package_data = True,
    packages=[
        'proso_models',
        'proso_models.management',
        'proso_models.management.commands',
        'proso_models.migrations',
        'proso_questions',
        'proso_questions.management',
        'proso_questions.management.commands',
        'proso_questions.migrations',
        'proso_flashcards',
        'proso_flashcards.management',
        'proso_flashcards.management.commands',
        'proso_flashcards.migrations',
        'proso_questions_client',
        'proso_questions_client.management',
        'proso_questions_client.management.commands',
        'proso_common',
        'proso_ab',
        'proso_ab.management',
        'proso_ab.migrations',
        'proso',
        'proso.django',
        'proso.models'
    ],
    install_requires=[
        'Django>=1.6,<1.7',
        'clint>=0.4.1',
        'django-debug-toolbar>=1.1',
        'django-flatblocks>=0.8',
        'django-ipware>=0.0.8',
        'django-lazysignup>=0.12.2',
        'django-social-auth>=0.7.28',
        'jsonschema>=2.4.0',
        'Markdown>=2.4.1',
        'numpy>=1.8.2',
        'Pillow>=2.6.0',
        'psycopg2>=2.5.4',
        'South>=0.8'
    ],
    license='Gnu GPL v3',
)
