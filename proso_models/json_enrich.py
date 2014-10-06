from proso.django.response import pass_get_parameters
from django.core.urlresolvers import reverse


def audit_url(request, json, nested):
    if 'object_type' not in json or json['object_type'] != 'value':
        return json
    url = reverse('audit', kwargs={'key': json['key']})
    url_suffix = ''
    if json['user_id']:
        url_suffix += '&user=%s' % json['user_id']
    if json['item_primary_id']:
        url_suffix += '&item=%s' % json['item_primary_id']
    if json['item_secondary_id']:
        url_suffix += '&item_secondary=%s' % json['item_secondary_id']
    if url_suffix:
        url += '?' + url_suffix[1:]
    json['audit_url'] = pass_get_parameters(request, url, ignore=['item', 'item_secondary', 'user'])
    return json
