import models


class ABMiddleware:

    def process_request(self, request):
        models.Experiment.objects.init_request(request)
