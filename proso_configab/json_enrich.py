from .models import ExperimentSetup


def experiment_setup_stats(request, json_list, nested):
    if 'stats' not in request.GET:
        return
    experiment_setup_ids = [e['id'] for e in json_list]
    stats = ExperimentSetup.objects.get_stats(experiment_setup_ids)
    for json_object in json_list:
        json_object['stats'] = stats[json_object['id']]
