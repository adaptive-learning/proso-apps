from django.core.exceptions import ImproperlyConfigured

DJANGO_READY = False

try:
    from proso_common.models import custom_config_filter
    from proso_models.models import Item
    DJANGO_READY = True
except (ImproperlyConfigured, ImportError):
    pass


class selected_item_context:

    def __init__(self, item, all_items):
        global DJANGO_READY
        if DJANGO_READY:
            parents = Item.objects.get_reachable_parents(all_items)[item]

            def _custom_config_filter(key, value):
                if key != 'selected_item_has_parent':
                    return None
                return int(value) in parents
            self._context = custom_config_filter(_custom_config_filter)
        else:
            self._context = None

    def __enter__(self):
        if self._context is not None:
            self._context.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        if self._context is not None:
            self._context.__exit__(exc_type, exc_value, traceback)
