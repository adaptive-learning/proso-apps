from models import Value
from proso.django.response import pass_get_parameters
from django.core.urlresolvers import reverse


def values(request, json_list, nested):
    if nested:
        return json_list
    object_ids = map(lambda x: x['id'], json_list)
    values = Value.objects.filter(experiment_id__in=object_ids)
    values_dict = {}
    for v in values:
        object_id = v.experiment_id
        found = values_dict.get(object_id, [])
        found.append(v.to_json(nested=True))
        values_dict[object_id] = found
    for json in json_list:
        json['values'] = values_dict.get(json['id'], [])
    return json_list


def url(request, json, nested):
    if 'object_type' in json and 'id' in json:
        json['url'] = pass_get_parameters(
            request,
            reverse('show_ab_' + json['object_type'], kwargs={'id': json['id']}),
            ['filter_column', 'filter_value']
        )
    return json
