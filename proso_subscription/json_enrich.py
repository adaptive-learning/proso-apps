from django.core.urlresolvers import reverse


def action_subscribe(request, json_list, nested):
    if not request.user.is_authenticated():
        return
    for desc in json_list:
        if 'actions' not in desc:
            desc['actions'] = {}
        desc['actions']['subscribe'] = reverse('subscription_subscribe', args=[desc['id']])
