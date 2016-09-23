from .models import CustomConfig
from collections import defaultdict
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db.models.sql.datastructures import EmptyResultSet
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from proso.django.request import json_body
from proso.django.response import render_json
from proso_common.models import get_tables_allowed_to_export, get_custom_exports, get_global_config
from time import time as time_lib
from wsgiref.util import FileWrapper
import hashlib
import json as json_lib
import logging
import os
import os.path
import urllib.parse


LOGGER = logging.getLogger('django.request')
JAVASCRIPT_LOGGER = logging.getLogger(getattr(settings, 'PROSO_JAVASCRIPT_LOGGER', 'javascript'))


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
    try:
        objs = get_fun(request, object_class)
        if 'db_orderby' in request.GET:
            objs = objs.order_by(('-' if 'desc' in request.GET else '') + request.GET['db_orderby'].strip('/'))
        if 'all' not in request.GET and 'json_orderby' not in request.GET:
            objs = objs[page * limit:(page + 1) * limit]
        cache_key = 'proso_common_sql_json_%s' % hashlib.sha1((str(objs.query) + str(to_json_kwargs)).encode()).hexdigest()
        cached = cache.get(cache_key)
        if should_cache and cached:
            list_objs = json_lib.loads(cached)
        else:
            list_objs = [x.to_json(**to_json_kwargs) for x in list(objs)]
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
    except EmptyResultSet:
        return render_json(request, [], template=template, help_text=show_more.__doc__)


@ensure_csrf_cookie
def log(request):
    """
    Log an event from the client to the server.

    POST parameters (JSON keys):
      message:
        description (str) of the logged event
      level:
        debug|info|warn|error
      data:
        additional data (JSON) describing the logged event
    """
    if request.method == "POST":
        log_dict = json_body(request.body.decode("utf-8"))
        if 'message' not in log_dict:
            return HttpResponseBadRequest('There is no message to log!')
        levels = {
            'debug': JAVASCRIPT_LOGGER.debug,
            'info': JAVASCRIPT_LOGGER.info,
            'warn': JAVASCRIPT_LOGGER.warn,
            'error': JAVASCRIPT_LOGGER.error,
        }
        log_fun = JAVASCRIPT_LOGGER.info
        if 'level' in log_dict:
            log_fun = levels[log_dict['level']]
        log_fun(log_dict['message'], extra={
            'request': request,
            'user': request.user.id if request.user.is_authenticated() else None,
            'client_data': json_lib.dumps(log_dict.get('data', {})),
        })
        return HttpResponse('ok', status=201)
    else:
        return render_json(request, {}, template='common_log_service.html', help_text=log.__doc__)


@login_required
def custom_config(request):
    """
    Save user-specific configuration property.

    POST parameters (JSON keys):
        app_name: application name for which the configuration property is
            valid (e.g., proso_models)
        key: name of the property (e.g., predictive_model.class)
        value: value of the property (number, string, boolean, ...,
            e.g, proso.models.prediction.PriorCurrentPredictiveModel)
        condition_key (optional): name of the condition which is used to filter
            the property (e.g., practice_filter)
        condition_value (optional): value for the condition filtering the
            property (e.g., [["context/world"],["category/state"]])
    """
    if request.method == 'POST':
        config_dict = json_body(request.body.decode('utf-8'))
        CustomConfig.objects.try_create(
            config_dict['app_name'],
            config_dict['key'],
            config_dict['value'],
            request.user.id,
            config_dict.get('condition_key') if config_dict.get('condition_key') else None,
            urllib.parse.unquote(config_dict.get('condition_value')) if config_dict.get('condition_value') else None
        )
        return config(request)
    else:
        return render_json(request, {}, template='common_custom_config.html', help_text=custom_config.__doc__)


def config(request):
    return render_json(request, get_global_config(), template='common_json.html')


def languages(request):
    """
    Returns languages that are available in the system.

    Returns Dict: language_code -> domain
    """
    return render_json(request,
                       settings.LANGUAGE_DOMAINS if hasattr(settings, 'LANGUAGE_DOMAINS') else
                       {"error": "Languages are not set. (Set LANGUAGE_DOMAINS in settings.py)"},
                       template='common_json.html', help_text=languages.__doc__)


def csv(request, filename=None):
    if not request.user.is_staff:
        response = {
            "error": "Permission denied: you need to be staff member. If you think you should be able to access logs, contact admins."}
        return render_json(request, response, status=401, template='common_json.html')
    if filename:
        return _csv_table(request, filename)
    else:
        return _csv_list(request)


def _csv_list(request):
    apps = defaultdict(dict)
    for app, app_data in get_tables_allowed_to_export().items():
        apps[app]['tables'] = list(map(lambda d: {'name': d[1], 'url': reverse('csv_table', kwargs={'filename': d[1]})}, app_data))
    for app, app_data in get_custom_exports().items():
        apps[app]['custom_exports'] = list(map(lambda name: {'name': name, 'url': reverse('csv_table', kwargs={'filename': name})}, app_data))
    return render_json(request, apps, template='common_json.html')


def _csv_table(request, filename):
    if filename not in [x[1] for xs in get_tables_allowed_to_export().values() for x in xs] and \
            filename not in [x for xs in get_custom_exports().values() for x in xs.keys()]:
        response = {
            "error": "the requested file '%s' is not valid" % filename
        }
        return render_json(request, response, status=400, template='common_json.html')
    download_file = settings.DATA_DIR + '/' + filename + ".csv"
    if not os.path.exists(download_file):
        response = {
            "error": "there is no data for the given table"
        }
        return render_json(request, response, status=204, template='common_json.html')
    response = HttpResponse(FileWrapper(open(download_file)), content_type='application/csv')
    response['Content-Length'] = os.path.getsize(download_file)
    response['Content-Disposition'] = 'attachment; filename=' + filename + '.csv'
    return response
