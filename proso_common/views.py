from proso.django.response import render_json
from proso_common.models import get_tables_allowed_to_export
from django.conf import settings
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse
import os
import os.path
from django.core.urlresolvers import reverse


def csv(request, table_name=None):
    if not request.user.is_staff:
        response = {
            "error": "Permission denied: you need to be staff member. If you think you should be able to access logs, contact admins."}
        return render_json(request, response, status=401, template='common_json.html')
    if table_name:
        return _csv_table(request, table_name)
    else:
        return _csv_list(request)


def _csv_list(request):
    response = map(
        lambda table_name: {'table': table_name, 'url': reverse('csv_table', kwargs={'table_name': table_name})},
        get_tables_allowed_to_export())
    return render_json(request, response, template='common_json.html')


def _csv_table(request, table_name):
    if table_name not in get_tables_allowed_to_export():
        response = {
            "error": "the requested table '%s' is not valid" % table_name
        }
        return render_json(request, response, status=400, template='common_json.html')
    zip_file = settings.DATA_DIR + '/' + table_name + ".zip"
    if not os.path.exists(zip_file):
        response = {
            "error": "there is no data for the given table"
        }
        return render_json(request, response, status=204, template='common_json.html')
    response = HttpResponse(FileWrapper(open(zip_file)), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=' + table_name
    return response
