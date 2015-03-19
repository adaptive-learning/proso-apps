# -*- coding: utf-8 -*-

"""
Django settings for testproject project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MEDIA_DIR = os.path.join(BASE_DIR, 'media')
DATA_DIR = os.path.join(BASE_DIR, 'data')
MEDIA_URL = '/media/'


ON_PRODUCTION = False
ON_STAGING = False

if 'PROSO_ON_PRODUCTION' in os.environ:
    ON_PRODUCTION = True
if 'PROSO_ON_STAGING' in os.environ:
    ON_STAGING = True
    DEBUG_TOOLBAR_PATCH_SETTINGS = False

if ON_PRODUCTION:
    DEBUG = False
else:
    DEBUG = True

TEMPLATE_DEBUG = DEBUG

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'really secret key'
if ON_PRODUCTION or ON_STAGING:
    SECRET_KEY = os.environ['PROSO_SECRET_KEY']

# Application definition

INSTALLED_APPS = (
    'debug_toolbar',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'flatblocks',
    'lazysignup',
    'proso_ab',
    'proso_common',
    'proso_models',
    'proso_questions',
    'proso_questions_client',
    'proso_user',
    'proso_feedback',
    'proso_flashcards',
    'social_auth',
    'testproject.testapp',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'proso_common.models.RequestMiddleware',
    'proso_ab.models.ABMiddleware',
    'proso_models.cache.RequestCacheMiddleware',
    'proso.django.log.RequestLogMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'proso_questions_client.middleware.AuthAlreadyAssociatedMiddleware',
)

ROOT_URLCONF = 'testproject.urls'


TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(BASE_DIR, '..', 'proso_questions', 'templates'),
    os.path.join(BASE_DIR, '..', 'proso_questions_client', 'templates'),
)

# Da
import sys
if 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'testproject.sqlite3')
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': os.getenv('PROSO_DATABASE_ENGINE', 'django.db.backends.postgresql_psycopg2'),
            'NAME': os.getenv('PROSO_DATABASE_NAME', 'proso_apps'),
            'USER': os.getenv('PROSO_DATABASE_USER', 'proso_apps'),
            'PASSWORD': os.getenv('PROSO_DATABASE_PASSWORD', 'proso_apps'),
            'HOST': os.getenv('PROSO_DATABASE_HOST', 'localhost'),
            'PORT': os.getenv('PROSO_DATABASE_PORT', None)
        }
    }

# Internationalization

USE_I18N = False

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)

STATIC_ROOT = os.path.join(BASE_DIR, '..', '..', 'static')
STATIC_URL = '/static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'lazysignup.backends.LazySignupBackend',
    'social_auth.backends.facebook.FacebookBackend',
    'social_auth.backends.google.GoogleOAuth2Backend',
)

FACEBOOK_APP_ID = os.getenv('PROSO_FACEBOOK_APP_ID', '')
FACEBOOK_API_SECRET = os.getenv('PROSO_FACEBOOK_API_SECRET', '')
FACEBOOK_EXTENDED_PERMISSIONS = ['email']

SOCIAL_AUTH_CREATE_USERS = True
SOCIAL_AUTH_FORCE_RANDOM_USERNAME = False
SOCIAL_AUTH_DEFAULT_USERNAME = 'socialauth_user'
LOGIN_ERROR_URL = '/login/error/'
SOCIAL_AUTH_ERROR_KEY = 'socialauth_error'
SOCIAL_AUTH_RAISE_EXCEPTIONS = False
GOOGLE_OAUTH2_CLIENT_ID = os.getenv('PROSO_GOOGLE_OAUTH2_CLIENT_ID', '')
GOOGLE_OAUTH2_CLIENT_SECRET = os.getenv('PROSO_GOOGLE_OAUTH2_CLIENT_SECRET', '')

# http://stackoverflow.com/questions/22005841/is-not-json-serializable-django-social-auth-facebook-login
SESSION_SERIALIZER='django.contrib.sessions.serializers.PickleSerializer'


ALLOWED_HOSTS = [
    '.autoskolachytre.cz',
]

LOGIN_REDIRECT_URL = '/'

SOCIAL_AUTH_DEFAULT_USERNAME = 'new_social_auth_user'

SOCIAL_AUTH_UID_LENGTH = 222
SOCIAL_AUTH_NONCE_SERVER_URL_LENGTH = 200
SOCIAL_AUTH_ASSOCIATION_SERVER_URL_LENGTH = 135
SOCIAL_AUTH_ASSOCIATION_HANDLE_LENGTH = 125


# http://stackoverflow.com/questions/4882377/django-manage-py-test-fails-table-already-exists
SOUTH_TESTS_MIGRATE = False

try:
    from hashes import HASHES
except ImportError:
    HASHES = {}
except SyntaxError:
    HASHES = {}

PROSO_PREDICTIVE_MODEL = 'proso.models.prediction.AlwaysLearningPredictiveModel'
PROSO_ENVIRONMENT = 'proso_models.models.DatabaseEnvironment'
PROSO_RECOMMENDATION = 'proso.models.recommendation.ScoreRecommendation'
PROSO_TEST_EVALUATOR = 'proso_questions.models.CategoryTestEvaluator'
PROSO_TEST_EVALUATOR_ARGS = [{
    u'Pravidla provozu na pozemních komunikacích': {
        'correct': 2,
        'answers': 10
    },
    u'Dopravní značky': {
        'correct': 1,
        'answers': 3
    },
    u'Zásady bezpečné jízdy': {
        'correct': 2,
        'answers': 4
    },
    u'Dopravní situace': {
        'correct': 4,
        'answers': 3
    },
    u'Předpisy o podmínkách provozu vozidel': {
        'correct': 1,
        'answers': 2
    },
    u'Předpisy související s provozem': {
        'correct': 2,
        'answers': 2
    },
    u'Zdravotnická příprava': {
        'correct': 1,
        'answers': 1
    }
}, 43]

FEEDBACK_TO = 'autoskolachytre@googlegroups.com'
FEEDBACK_TO = 'slaweet@seznam.cz'
FEEDBACK_DOMAIN = 'autoskolachytre.cz'

EMAIL_HOST = 'localhost'
EMAIL_PORT = 25

LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'request': {
            'level': 'DEBUG',
            'class': 'proso.django.log.RequestHandler',
            'formatter': 'simple'
        }
    },
    'formatters': {
        'simple': {
            'format': '[%(asctime)s] %(levelname)s "%(message)s"'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['console', 'request'],
            'propagate': True,
            'level': 'DEBUG'
        }
    }
}
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.join(DATA_DIR, '.django_cache'),
    }
}

PROSO_FLASHCARDS = {}
