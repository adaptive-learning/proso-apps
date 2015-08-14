from models import ExperimentSetup


def experiment_setup_stats(request, json_list, nested):
    answers_per_user = int(request.GET.get('answers_per_user', 10))
    experiment_setup_ids = map(lambda e: e['id'], json_list)
    stats = ExperimentSetup.objects.get_stats(experiment_setup_ids, answers_per_user=answers_per_user)
    for json_object in json_list:
        json_object['stats'] = stats[json_object['id']]
