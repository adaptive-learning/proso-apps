from proso.django.response import render_json, render
from proso_common.management.commands import analyse
from proso_common.models import get_tables_allowed_to_export
from django.conf import settings
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse
import os
import os.path
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from time import time as time_lib
import hashlib
from django.core.cache import cache
import json as json_lib
import logging
from proso.django.config import get_global_config


LOGGER = logging.getLogger('django.request')


def show_one(request, post_process_fun, object_class, id, template='common_json.html'):
    """
    Return object of the given type with the specified identifier.

    GET parameters:
      user:
        identifier of the current user
      stats:
        turn on the enrichment of the objects by some statistics
      html
        turn on the HTML version of the API
    """
    obj = get_object_or_404(object_class, pk=id)
    json = post_process_fun(request, obj)
    return render_json(request, json, template=template, help_text=show_one.__doc__)


def show_more(request, post_process_fun, get_fun, object_class, should_cache=True, template='common_json.html', to_json_kwargs=None):
    """
    Return list of objects of the given type.

    GET parameters:
      limit:
        number of returned objects (default 10, maximum 100)
      page:
        current page number
      filter_column:
        column name used to filter the results
      filter_value:
        value for the specified column used to filter the results
      user:
        identifier of the current user
      all:
        return all objects available instead of paging; be aware this parameter
        can be used only for objects for wich the caching is turned on
      db_orderby:
        database column which the result should be ordered by
      json_orderby:
        field of the JSON object which the result should be ordered by, it is
        less effective than the ordering via db_orderby; be aware this parameter
        can be used only for objects for which the caching is turned on
      desc
        turn on the descending order
      stats:
        turn on the enrichment of the objects by some statistics
      html
        turn on the HTML version of the API
      environment
        turn on the enrichment of the related environment values
    """
    if not should_cache and 'json_orderby' in request.GET:
        return render_json(request, {
            'error': "Can't order the result according to the JSON field, because the caching for this type of object is turned off. See the documentation."
            },
            template='questions_json.html', help_text=show_more.__doc__, status=501)
    if not should_cache and 'all' in request.GET:
        return render_json(request, {
            'error': "Can't get all objects, because the caching for this type of object is turned off. See the documentation."
            },
            template='questions_json.html', help_text=show_more.__doc__, status=501)
    if to_json_kwargs is None:
        to_json_kwargs = {}
    time_start = time_lib()
    limit = min(int(request.GET.get('limit', 10)), 100)
    page = int(request.GET.get('page', 0))
    objs = get_fun(request, object_class)
    if 'db_orderby' in request.GET:
        objs = objs.order_by(('-' if 'desc' in request.GET else '') + request.GET['db_orderby'])
    if 'all' not in request.GET and 'json_orderby' not in request.GET:
        objs = objs[page * limit:(page + 1) * limit]
    cache_key = 'proso_common_sql_json_%s' % hashlib.sha1(str(objs.query).decode('utf-8') + str(to_json_kwargs)).hexdigest()
    cached = cache.get(cache_key)
    if should_cache and cached:
        list_objs = json_lib.loads(cached)
    else:
        list_objs = map(lambda x: x.to_json(**to_json_kwargs), list(objs))
        if should_cache:
            cache.set(cache_key, json_lib.dumps(list_objs), 60 * 60 * 24 * 30)
    LOGGER.debug('loading objects in show_more view took %s seconds', (time_lib() - time_start))
    json = post_process_fun(request, list_objs)
    if 'json_orderby' in request.GET:
        time_before_json_sort = time_lib()
        json.sort(key=lambda x: (-1 if 'desc' in request.GET else 1) * x[request.GET['json_orderby']])
        if 'all' not in request.GET:
            json = json[page * limit:(page + 1) * limit]
        LOGGER.debug('sorting objects according to JSON field took %s seconds', (time_lib() - time_before_json_sort))
    return render_json(request, json, template=template, help_text=show_more.__doc__)


def config(request):
    return render_json(request, get_global_config(), template='common_json.html')


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
    response['Content-Disposition'] = 'attachment; filename=' + table_name + '.zip'
    return response


def analysis(request, app_name=None):
    data = {}
    if app_name is None:
        data["apps"] = list(os.listdir(analyse.OUTPUT_DIR))
    else:
        data["imgs"] = map(lambda i: "analysis/{}/{}".format(app_name, i),
                           os.listdir(os.path.join(analyse.OUTPUT_DIR, app_name)))
        data["app_name"] = app_name
    return render(request, 'common_analysis.html', data)
