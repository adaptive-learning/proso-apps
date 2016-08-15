from proso_models.models import get_filter


class InitPracticeFilterMiddleware(object):

    def process_request(self, request):
        if 'filter' in request.GET:
            get_filter(request)
