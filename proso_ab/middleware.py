import models
import logging

LOGGER = logging.getLogger(__name__)


class ABMiddleware:

    def process_request(self, request):
        models.Experiment.objects.init_request(request)
        LOGGER.debug('initialized AB experiments for user %s: %s' % (str(request.user.id), str(request.session.get('ab_experiment_values', []))))
