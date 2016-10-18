from proso_common.models import custom_config_filter
from proso_models.models import Item


class selected_item_context:

    def __init__(self, item, all_items):
        parents = Item.objects.get_reachable_parents(all_items)[item]

        def _custom_config_filter(key, value):
            if key != 'selected_item_has_parent':
                return None
            return int(value) in parents
        self._context = custom_config_filter(_custom_config_filter)

    def __enter__(self):
        self._context.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        self._context.__exit__(exc_type, exc_value, traceback)
