from .models import ExperimentSetup


def experiment_setup_stats(request, json_list, nested):
    if 'stats' in request.GET:
        return
    answers_per_user = int(request.GET.get('answers_per_user', 10))
    learning_curve_length = int(request.GET.get('learning_curve_length', 5))
    learning_curve_max_users = int(request.GET.get('learning_curve_max_users', 1000))
    experiment_setup_ids = [e['id'] for e in json_list]
    stats = ExperimentSetup.objects.get_stats(experiment_setup_ids,
        answers_per_user=answers_per_user,
        learning_curve_length=learning_curve_length,
        learning_curve_max_users=learning_curve_max_users)
    for json_object in json_list:
        json_object['stats'] = stats[json_object['id']]
