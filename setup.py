from setuptools import setup, find_packages
import proso.release
import os

VERSION = proso.release.VERSION

setup(
    name='proso-apps',
    version=VERSION,
    description='General library for applications in PROSO projects',
    author='Jan Papousek, Vit Stanislav',
    author_email='jan.papousek@gmail.com, slaweet@seznam.cz',
    namespace_packages = ['proso', 'proso.django'],
    include_package_data = True,
    packages=[
        'proso',
        'proso.django',
        'proso.models',
        'proso_ab',
        'proso_ab.management',
        'proso_ab.management.commands',
        'proso_ab.migrations',
        'proso_common',
        'proso_common.management',
        'proso_common.management.commands',
        'proso_feedback',
        'proso_flashcards',
        'proso_flashcards.management',
        'proso_flashcards.management.commands',
        'proso_flashcards.migrations',
        'proso_models',
        'proso_models.management',
        'proso_models.management.commands',
        'proso_models.migrations',
        'proso_questions',
        'proso_questions.management',
        'proso_questions.management.commands',
        'proso_questions.migrations',
        'proso_questions_client',
        'proso_questions_client.management',
        'proso_questions_client.management.commands',
        'proso_user',
        'proso_user.migrations'
    ],
    install_requires=[
        'Django>=1.6,<1.7',
        'Markdown>=2.4.1',
        'Pillow>=2.6.0',
        'South>=0.8',
        'clint>=0.4.1',
        'django-debug-toolbar>=1.1',
        'django-flatblocks>=0.8',
        'django-ipware>=0.0.8',
        'django-lazysignup>=0.12.2',
        'django-social-auth>=0.7.28',
        'jsonschema>=2.4.0',
        'numpy>=1.8.2',
        'psycopg2>=2.5.4',
        'PyYAML==3.11',
        'ua-parser==0.3.6',
        'user-agents==0.3.1'
    ],
    license='Gnu GPL v3',
)
