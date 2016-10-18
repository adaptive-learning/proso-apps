from .models import Subscription
from proso_common.models import add_custom_config_filter


class CustomConfigFilterForActiveSubscription(object):

    def process_request(self, request):
        def _filter(key, value):
            if key != 'has_active_subscription':
                return None
            return Subscription.objects.is_active(request.user, value)
        add_custom_config_filter(_filter)
