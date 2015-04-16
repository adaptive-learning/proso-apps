import json
from proso.django.config import get_global_config


def config_processor(request):
    config = get_global_config()
    return {
        'config_json': json.dumps(config),
        'config': config
    }
