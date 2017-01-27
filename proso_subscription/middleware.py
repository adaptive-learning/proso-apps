from .models import Subscription, get_forbidden_categories
from proso_common.models import add_custom_config_filter
from proso_models.models import add_item_restrictor


class CustomConfigFilterForActiveSubscription(object):

    def process_request(self, request):
        def _filter(key, value):
            if key != 'has_active_subscription':
                return None
            return Subscription.objects.is_active(request.user, value)
        add_custom_config_filter(_filter)


class ItemRestrictor(object):

    def process_request(self, request):

        def _restrictor():
            return get_forbidden_categories(request.user)
        add_item_restrictor(_restrictor)
