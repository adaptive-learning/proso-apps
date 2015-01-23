from django.conf import settings
import importlib
from threading import currentThread


_request_initialized = False
_current_request = {}


class RequestMiddleware:
    def process_request(self, request):
        global _request_initialized
        _request_initialized = True
        _current_request[currentThread()] = request


def get_current_request(force=True):
    if not force and not _request_initialized:
        return None
    assert _request_initialized, 'RequestMiddleware is not loaded'
    return _current_request[currentThread()]


def get_tables_allowed_to_export():
    tables = []
    for app in settings.INSTALLED_APPS:
        try:
            app_models = importlib.import_module('%s.models' % app)
            if not hasattr(app_models, 'PROSO_MODELS_TO_EXPORT'):
                continue
            tables += map(lambda model: model._meta.db_table, app_models.PROSO_MODELS_TO_EXPORT)
        except ImportError:
            continue
    return tables
