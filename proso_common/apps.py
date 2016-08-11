from django.apps import AppConfig as OAppConfig
from django.conf import settings


MIDDLEWARE_CLASSES = [
    'proso_common.models.CommonMiddleware',
    'proso_common.middleware.ToolbarMiddleware',
    'proso_common.middleware.ErrorMiddleware',
    'proso_common.middleware.AuthAlreadyAssociatedMiddleware',

]


class AppConfig(OAppConfig):

    name = 'proso_common'

    def ready(self):
        for middleware in MIDDLEWARE_CLASSES:
            if middleware not in settings.MIDDLEWARE_CLASSES:
                settings.MIDDLEWARE_CLASSES = settings.MIDDLEWARE_CLASSES + (middleware, )
