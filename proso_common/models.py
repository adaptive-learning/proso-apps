from django.conf import settings
import importlib


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
