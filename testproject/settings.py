# -*- coding: utf-8 -*-

"""
Django settings for testproject project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from django.conf import settings
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
DATA_DIR = os.path.join(BASE_DIR, 'data')
MEDIA_URL = '/media/'


TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

DEBUG = True

TEMPLATE_DEBUG = DEBUG

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'really secret key'

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
    'proso_configab',
    'proso_models',
    'proso_questions',
    'proso_user',
    'proso_feedback',
    'proso_flashcards',
    'social.apps.django_app.default',
    'testproject.testapp',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'proso_common.middleware.ToolbarMiddleware',
    'proso_common.middleware.ErrorMiddleware',
    'proso_common.models.CommonMiddleware',
    'proso.django.request.RequestMiddleware',
    'proso.django.config.ConfigMiddleware',
    'proso_ab.models.ABMiddleware',
    'proso.django.cache.RequestCacheMiddleware',
    'proso.django.log.RequestLogMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'proso_questions_client.middleware.AuthAlreadyAssociatedMiddleware',
)

ROOT_URLCONF = 'testproject.urls'

TEMPLATE_CONTEXT_PROCESSORS = \
    settings.TEMPLATE_CONTEXT_PROCESSORS + ("proso_common.context_processors.config_processor", )

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(BASE_DIR, '..', 'proso_questions', 'templates'),
    os.path.join(BASE_DIR, '..', 'proso_questions_client', 'templates'),
)

if TESTING:
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

USE_I18N = True

USE_L10N = True

USE_TZ = False

from django.utils.translation import ugettext_lazy as _

LANGUAGES = (
    ('en', _('English')),
    ('cs', _('Czech')),
)
LOCALE_PATHS = (os.path.join(BASE_DIR, "locale"), )

# Static files (CSS, JavaScript, Images)

STATIC_ROOT = os.path.join(BASE_DIR, '..', 'static')
STATIC_URL = '/static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'lazysignup.backends.LazySignupBackend',
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.google.GoogleOAuth2',
)

SOCIAL_AUTH_FACEBOOK_KEY = os.getenv('PROSO_FACEBOOK_APP_ID', '955349341155915')
SOCIAL_AUTH_FACEBOOK_SECRET = os.getenv('PROSO_FACEBOOK_API_SECRET', '1afe2e6e6ccc3266d81708c89d4515d4')
SOCIAL_AUTH_FACEBOOK_EXTENDED_PERMISSIONS = ['email']

SOCIAL_AUTH_CREATE_USERS = True
SOCIAL_AUTH_FORCE_RANDOM_USERNAME = False
SOCIAL_AUTH_DEFAULT_USERNAME = 'socialauth_user'
LOGIN_ERROR_URL = '/login/error/'
SOCIAL_AUTH_ERROR_KEY = 'socialauth_error'
SOCIAL_AUTH_RAISE_EXCEPTIONS = False
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('PROSO_GOOGLE_OAUTH2_CLIENT_ID', '191094260688-97ergmtbuj34jf518ol60cuili58aml9.apps.googleusercontent.com')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('PROSO_GOOGLE_OAUTH2_CLIENT_SECRET', 'blQDABue66taqP__DVAHHb_Y')
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/user/close_popup/'

# http://stackoverflow.com/questions/22005841/is-not-json-serializable-django-social-auth-facebook-login
SESSION_SERIALIZER='django.contrib.sessions.serializers.PickleSerializer'


ALLOWED_HOSTS = []

LOGIN_REDIRECT_URL = '/'

SOCIAL_AUTH_DEFAULT_USERNAME = 'new_social_auth_user'

SOCIAL_AUTH_UID_LENGTH = 222
SOCIAL_AUTH_NONCE_SERVER_URL_LENGTH = 200
SOCIAL_AUTH_ASSOCIATION_SERVER_URL_LENGTH = 135
SOCIAL_AUTH_ASSOCIATION_HANDLE_LENGTH = 125


try:
    from hashes import HASHES
except ImportError:
    HASHES = {}
except SyntaxError:
    HASHES = {}

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
        },
        'javascript': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG'
        }
    }
}
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    },
    'disk': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.join(BASE_DIR, "data"),
    }
}

PROSO_JS_FILES = ['dist/js/bower-libs.js']
PROSO_FLASHCARDS = {}
