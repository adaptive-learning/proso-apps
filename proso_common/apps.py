from django.apps import AppConfig as OAppConfig
from django.conf import settings
import importlib


MIDDLEWARE_CLASSES = [
    'proso.django.request.RequestMiddleware',
    'proso.django.config.ConfigMiddleware',
    'proso.django.cache.RequestCacheMiddleware',
    'proso.django.log.RequestLogMiddleware',
    'proso_common.models.CommonMiddleware',
    'proso_common.middleware.ToolbarMiddleware',
    'proso_common.middleware.ErrorMiddleware',
    'proso_common.middleware.AuthAlreadyAssociatedMiddleware',

]


class AppConfig(OAppConfig):

    name = 'proso_common'

    def ready(self):
        for middleware in MIDDLEWARE_CLASSES:
            install_middleware(middleware)
        for app in settings.INSTALLED_APPS:
            apps_module_name = app + '.apps'
            spec = importlib.util.find_spec(apps_module_name)
            if spec is None:
                continue
            apps_module = importlib.import_module(apps_module_name)
            if not hasattr(apps_module, 'MIDDLEWARE_CLASSES'):
                continue
            for middleware in getattr(apps_module, 'MIDDLEWARE_CLASSES'):
                install_middleware(middleware)


def install_middleware(middleware):
    if middleware not in settings.MIDDLEWARE_CLASSES:
        print('installing middleware', middleware)
        settings.MIDDLEWARE_CLASSES = settings.MIDDLEWARE_CLASSES + (middleware, )
