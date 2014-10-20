import os
import sys

DIRNAME = os.path.abspath(os.path.dirname(__file__))
sys.path.append(DIRNAME)
os.environ['DJANGO_SETTINGS_MODULE'] = 'proso_client.settings'

from django.core.handlers.wsgi import WSGIHandler


class WSGIEnvironment(WSGIHandler):
    def __call__(self, environ, start_response):
        for k, v in environ.iteritems():
            if isinstance(k, str) and k.startswith('DRIVING_SCHOOL'):
                os.environ[k] = v
        return super(WSGIEnvironment, self).__call__(environ, start_response)


application = WSGIEnvironment()
