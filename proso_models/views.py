from .models import get_environment, get_predictive_model, get_item_selector, get_active_environment_info, \
    Answer, Item, recommend_users as models_recommend_users, PracticeContext, PracticeSet,\
    learning_curve as models_learning_curve, get_filter, get_mastery_trashold, get_time_for_knowledge_overview, \
    survival_curve_answers as models_survival_curve_answers, survival_curve_time as models_survival_curve_time
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction, connection
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.translation import ugettext as _
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import ensure_csrf_cookie
from lazysignup.decorators import allow_lazy_user
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from proso.django.cache import cache_page_conditional
from proso.django.enrichment import enrich_json_objects_by_object_type
from proso.django.request import is_time_overridden, get_time, get_language, load_query_json
from proso.django.response import render, render_json, BadRequestException
from proso.list import flatten
from proso.time import timer
from proso_common.models import get_config
from proso_user.models import get_user_id
from random import sample
import datetime
import json
import logging
import proso.svg
import proso_common.views
from django.conf import settings


LOGGER = logging.getLogger('django.request')


@cache_page_conditional(
    condition=lambda request, args, kwargs: 'stats' not in request.GET and kwargs['object_class'] not in [PracticeSet])
def show_one(request, object_class, id):
    return proso_common.views.show_one(
        request, enrich_json_objects_by_object_type, object_class, id, template='models_json.html')


@cache_page_conditional(
    condition=lambda request, args, kwargs: 'stats' not in request.GET and kwargs['object_class'] not in [PracticeSet])
def show_more(request, object_class, should_cache=True):

    to_json_kwargs = {}

    def _load_objects(request, object_class):
        objs = object_class.objects
        if hasattr(objs, 'prepare_related'):
            objs = objs.prepare_related()
        db_filter = proso_common.views.get_db_filter(request)
        objs = objs.all() if db_filter is None else objs.filter(**db_filter)
        if object_class == PracticeSet:
            user_id = get_user_id(request, allow_override=True)
            objs = objs.filter(answer__user_id=user_id).order_by('-id')
        return objs

    return proso_common.views.show_more(
        request, enrich_json_objects_by_object_type, _load_objects, object_class,
        should_cache=should_cache, template='models_json.html', to_json_kwargs=to_json_kwargs)


@allow_lazy_user
def status(request):
    user_id = get_user_id(request)
    time = get_time(request)
    environment = get_environment()
    if is_time_overridden(request):
        environment.shift_time(time)
    return render_json(request, {
        'object_type': 'status',
        'number_of_answers': environment.number_of_answers(user=user_id),
        'number_of_correct_answers': environment.number_of_correct_answers(user=user_id),
        'environment_info': get_active_environment_info(),
    }, template='models_json.html')


@cache_page_conditional(condition=lambda request, args, kwargs: 'stats' not in request.GET, cache='file' if 'file' in settings.CACHES else None)
def to_practice(request):
    practice_filter = get_filter(request)
    item_ids = Item.objects.filter_all_reachable_leaves(practice_filter, get_language(request))
    if len(item_ids) == 0:
        return render_json(request, {
            'error': _('There is no item for the given filter to practice.'),
            'error_type': 'empty_practice'
        }, status=404, template='models_json.html')
    result = [Item.objects.item_id_to_json(item_id) for item_id in item_ids]
    return render_json(request, result, template='models_json.html', help_text=to_practice.__doc__)


@cache_page(60 * 60 * 24 * 7)
def to_practice_counts(request):
    """
    Get number of items available to practice.

    filters:                -- use this or body
      json as in BODY
    language:
      language of the items

    BODY
      json in following format:
      {
        "#identifier": []         -- custom identifier (str) and filter
        ...
      }
    """
    data = None
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))["filters"]
    if "filters" in request.GET:
        data = load_query_json(request.GET, "filters")
    if data is None or len(data) == 0:
        return render_json(request, {}, template='models_json.html', help_text=to_practice_counts.__doc__)
    language = get_language(request)
    timer('to_practice_counts')
    filter_names, filter_filters = list(zip(*sorted(data.items())))
    reachable_leaves = Item.objects.filter_all_reachable_leaves_many(filter_filters, language)
    response = {
        group_id: {
            'filter': data[group_id],
            'number_of_items': len(items),
        }
        for group_id, items in zip(filter_names, reachable_leaves)
    }
    LOGGER.debug("to_practice_counts - getting items in groups took %s seconds", (timer('to_practice_counts')))
    return render_json(request, response, template='models_json.html', help_text=to_practice_counts.__doc__)


@allow_lazy_user
def answers(request):
    limit = min(int(request.GET.get('limit', 10)), 1000)
    user_id = get_user_id(request)
    item_ids = Item.objects.filter_all_reachable_leaves(get_filter(request), get_language(request))
    found_answers = Answer.objects.answers(Answer.objects.filter(item_asked_id__in=item_ids, user_id=user_id).order_by('-id').values_list('id', flat=True)[:limit])
    return render_json(request, found_answers, template='models_json.html', help_text=answers.__doc__)


def practice_image(request):
    user_id = get_user_id(request)
    limit = min(int(request.GET.get('limit', 10)), 100)
    item_ids = Item.objects.filter_all_reachable_leaves(get_filter(request), get_language(request))
    answers = Answer.objects.filter(user_id=user_id).filter(item_asked_id__in=item_ids).order_by('-id')[:limit]
    predictive_model = get_predictive_model()
    environment = get_environment()
    predictions = predictive_model.predict_more_items(environment, user=-1, items=item_ids, time=get_time_for_knowledge_overview(request))
    items_in_order = list(zip(*sorted(zip(predictions, item_ids), reverse=True)))[1] if len(item_ids) > 1 else []
    item_prediction = dict(list(zip(item_ids, predictions)))
    item_position = dict(list(zip(items_in_order, list(range(len(item_ids))))))
    svg = proso.svg.Printer()
    answers = sorted(list(answers), key=lambda a: a.id)
    SQUARE_SIZE = 10
    OFFSET_X = SQUARE_SIZE
    OFFSET_Y = SQUARE_SIZE * 3
    for i, item in enumerate(items_in_order):
        svg.print_square(OFFSET_X + SQUARE_SIZE * i, OFFSET_Y - SQUARE_SIZE, SQUARE_SIZE, int(255 * item_prediction[item]))
    for i, answer in enumerate(answers):
        for j in range(len(items_in_order)):
            svg.print_square(OFFSET_X + SQUARE_SIZE * j, OFFSET_Y + SQUARE_SIZE * i, SQUARE_SIZE, 255, border_color=200)
        color = 'green' if answer.item_asked_id == answer.item_answered_id else 'red'
        svg.print_square(
            OFFSET_X + SQUARE_SIZE * item_position[answer.item_asked_id],
            OFFSET_Y + SQUARE_SIZE * i, SQUARE_SIZE, color, border_color=0)
        svg.print_text(OFFSET_X + SQUARE_SIZE * (len(items_in_order) + 1), OFFSET_Y + SQUARE_SIZE * i + 0.8 * SQUARE_SIZE, answer.time.strftime('%H:%M:%S %Y-%m-%d'), font_size=10)
    return HttpResponse(str(svg), content_type="image/svg+xml")


def answers_per_month(request):
    try:
        from pylab import rcParams
        import matplotlib.pyplot as plt
        import pandas
        import seaborn as sns
    except ImportError:
        return HttpResponse('Can not import python packages for analysis.', status=503)
    categories = load_query_json(request.GET, "categories", "[]")
    translated = Item.objects.translate_identifiers(categories, get_language(request))
    translated_inverted = {item: name for name, item in translated.items()}
    children = pandas.DataFrame([
        {'item': item, 'category': translated_inverted[category]}
        for category, items in Item.objects.get_reachable_children(
            list(translated.values()), get_language(request)
        ).items()
        for item in items
    ])
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT item_id, date_part('month', time), COUNT(1)
            FROM proso_models_answer
            GROUP BY 1, 2
            '''
        )
        data = []
        for item, month, answers in cursor:
            data.append({
                'item': item,
                'month': month,
                'answers': answers,
            })
    data = pandas.DataFrame(data)
    if len(children) == 0:
        data['category'] = data['item'].apply(lambda i: 'category/all')
    else:
        data = pandas.merge(data, children, on='item', how='inner')

    if 'percentage' in request.GET:
        def _percentage(group):
            total = group['answers'].sum()
            return group.groupby('category').apply(lambda g: 100 * g['answers'].sum() / total).reset_index().rename(columns={0: 'answers'})
        data = data.groupby('month').apply(_percentage).reset_index()

    def _apply(group):
        group['answers_cumsum'] = group['answers'].cumsum()
        return group
    data = data.sort_values(by=['category'], ascending=False).groupby('month').apply(_apply)
    data['month'] = data['month'].astype(int)
    sns.set(style='white')
    rcParams['figure.figsize'] = 15, 10
    palette = sns.color_palette("hls", max(5, len(categories)))
    fig = plt.figure()
    for i, category in enumerate(sorted(data['category'].unique())):
        item_data = data[data['category'] == category]
        sns.barplot(
            x='month',
            y='answers_cumsum',
            data=item_data,
            label=category.split('/')[1],
            color=palette[i % len(palette)],
            ci=None
        )
    plt.ylabel('Answers' + (' (%)' if 'percentage' in request.GET else ''))
    plt.xlabel('Month')
    plt.title('Answers per Month')
    if 'percentage' in request.GET:
        plt.ylim(0, 100)
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    response = HttpResponse(content_type='image/png')
    canvas = FigureCanvas(fig)
    canvas.print_png(response)
    return response


@ensure_csrf_cookie
@allow_lazy_user
@transaction.atomic
def answer(request):
    """
    Save the answer.

    GET parameters:
        html:
            turn on the HTML version of the API

    BODY
    json in following format:
    {
        "answer": #answer,                          -- for one answer
        "answers": [#answer, #answer, #answer ...]  -- for multiple answers
    }

    answer = {
        "answer_class": str,            -- class of answer to save (e.g., flashcard_answer)
        "response_time": int,           -- response time in milliseconds
        "meta": "str"                   -- optional information
        "time_gap": int                 -- waiting time in frontend in seconds
        ...                             -- other fields depending on aswer type
                                          (see from_json method of Django model class)
    }
    """
    if request.method == 'GET':
        return render(request, 'models_answer.html', {}, help_text=answer.__doc__)
    elif request.method == 'POST':
        practice_filter = get_filter(request)
        practice_context = PracticeContext.objects.from_content(practice_filter)
        saved_answers = _save_answers(request, practice_context, True)
        return render_json(request, saved_answers, status=200, template='models_answer.html')
    else:
        return HttpResponseBadRequest("method %s is not allowed".format(request.method))


@ensure_csrf_cookie
@allow_lazy_user
def user_stats(request):
    """
    Get user statistics for selected groups of items

    time:
      time in format '%Y-%m-%d_%H:%M:%S' used for practicing
    user:
      identifier of the user (only for stuff users)
    username:
      username of user (only for users with public profile)
    filters:                -- use this or body
      json as in BODY
    mastered:
      use model to compute number of mastered items - can be slowed
    language:
      language of the items

    BODY
      json in following format:
      {
        "#identifier": []         -- custom identifier (str) and filter
        ...
      }
    """
    timer('user_stats')
    response = {}
    data = None
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))["filters"]
    if "filters" in request.GET:
        data = load_query_json(request.GET, "filters")
    if data is None:
        return render_json(request, {}, template='models_user_stats.html', help_text=user_stats.__doc__)
    environment = get_environment()
    if is_time_overridden(request):
        environment.shift_time(get_time(request))
    user_id = get_user_id(request)
    language = get_language(request)
    filter_names, filter_filters = list(zip(*sorted(data.items())))
    reachable_leaves = Item.objects.filter_all_reachable_leaves_many(filter_filters, language)
    all_leaves = sorted(list(set(flatten(reachable_leaves))))
    answers = environment.number_of_answers_more_items(all_leaves, user_id)
    correct_answers = environment.number_of_correct_answers_more_items(all_leaves, user_id)
    if request.GET.get("mastered"):
        timer('user_stats_mastered')
        mastery_threshold = get_mastery_trashold()
        predictions = Item.objects.predict_for_overview(environment, user_id, all_leaves)
        mastered = dict(list(zip(all_leaves, [p >= mastery_threshold for p in predictions])))
        LOGGER.debug("user_stats - getting predictions for items took %s seconds", (timer('user_stats_mastered')))
    for identifier, items in zip(filter_names, reachable_leaves):
        if len(items) == 0:
            response[identifier] = {
                "filter": data[identifier],
                "number_of_items": 0,
            }
        else:
            response[identifier] = {
                "filter": data[identifier],
                "number_of_items": len(items),
                "number_of_practiced_items": sum(answers[i] > 0 for i in items),
                "number_of_answers": sum(answers[i] for i in items),
                "number_of_correct_answers": sum(correct_answers[i] for i in items),
            }
            if request.GET.get("mastered"):
                response[identifier]["number_of_mastered_items"]= sum(mastered[i] for i in items)
    return render_json(request, response, template='models_user_stats.html', help_text=user_stats.__doc__)


@ensure_csrf_cookie
@allow_lazy_user
@transaction.atomic
def practice(request):
    """
    Return the given number of questions to practice adaptively. In case of
    POST request, try to save the answer(s).

    GET parameters:
        filter:
            list of lists of identifiers (may be prefixed by minus sign to
            mark complement)
        language:
            language (str) of items
        avoid:
            list of item ids to avoid
        limit:
            number of returned questions (default 10, maximum 100)
        time:
            time in format '%Y-%m-%d_%H:%M:%S' used for practicing
        user:
            identifier for the practicing user (only for stuff users)
        stats:
            turn on the enrichment of the objects by some statistics
        html:
            turn on the HTML version of the API

    BODY:
        see answer resource
    """
    if request.user.id is None:  # Google Bot
        return render_json(request, {
            'error': _('There is no user available for the practice.'),
            'error_type': 'user_undefined'
        }, status=400, template='models_json.html')

    limit = min(int(request.GET.get('limit', 10)), 100)
    # prepare
    user = get_user_id(request)
    time = get_time(request)
    avoid = load_query_json(request.GET, "avoid", "[]")
    practice_filter = get_filter(request)
    practice_context = PracticeContext.objects.from_content(practice_filter)
    environment = get_environment()
    item_selector = get_item_selector()
    if is_time_overridden(request):
        environment.shift_time(time)

    # save answers
    if request.method == 'POST':
        _save_answers(request, practice_context, False)
    elif request.method == 'GET':
        PracticeSet.objects.filter(answer__user_id=request.user.id).update(finished=True)

    if limit > 0:
        item_ids = Item.objects.filter_all_reachable_leaves(practice_filter, get_language(request))
        item_ids = list(set(item_ids) - set(avoid))
        limit_size = get_config('proso_models', 'practice.limit_item_set_size_to_select_from', default=None)
        if limit_size is not None and limit_size < len(item_ids):
            item_ids = sample(item_ids, limit_size)
        if len(item_ids) == 0:
            return render_json(request, {
                'error': _('There is no item for the given filter to practice.'),
                'error_type': 'empty_practice'
            }, status=404, template='models_json.html')
        selected_items, meta = item_selector.select(environment, user, item_ids, time, practice_context.id, limit, items_in_queue=len(avoid))
        result = []
        for item, item_meta in zip(selected_items, meta):
            question = {
                'object_type': 'question',
                'payload': Item.objects.item_id_to_json(item),
            }
            if item_meta is not None:
                question['meta'] = item_meta
            result.append(question)
    else:
        result = []

    return render_json(request, result, template='models_json.html', help_text=practice.__doc__)


def survival_curve(request, metric):
    '''
    Shows a learning curve based on the randomized testing.

    GET parameters:
      length:
        length of the learning curve
      context:
        JSON representing the practice context
      all_users:
        if present stop filtering users based on the minimal number of testing
        answers (=length)
    '''
    practice_filter = get_filter(request, force=False)
    context = None if practice_filter is None else PracticeContext.objects.from_content(practice_filter).id
    if metric == 'answers':
        length = int(request.GET.get('length', 100))
        models_survival_curve_answers(length, context=context)
    else:
        length = int(request.GET.get('length', 600))
        models_survival_curve_time(length, context=context)
    return render_json(
        request,
        models_learning_curve(length, context=context),
        template='models_json.html', help_text=learning_curve.__doc__)


def learning_curve(request):
    '''
    Shows a learning curve based on the randomized testing.

    GET parameters:
      length:
        length of the learning curve
      context:
        JSON representing the practice context
      all_users:
        if present stop filtering users based on the minimal number of testing
        answers (=length)
    '''
    practice_filter = get_filter(request, force=False)
    context = None if practice_filter is None else PracticeContext.objects.from_content(practice_filter).id
    length = int(request.GET.get('length', 10))
    models_survival_curve_answers(length * 10, context=context)
    return render_json(
        request,
        models_learning_curve(length, context=context),
        template='models_json.html', help_text=learning_curve.__doc__)


@staff_member_required
def recommend_users(request):
    '''
    Recommend users for further analysis.

    GET parameters:
      register_min:
        minimal date of user's registration ('%Y-%m-%d')
      register_max:
        maximal date of user's registration ('%Y-%m-%d')
      number_of_answers_min:
        minimal number of user's answers
      number_of_answers_max:
        maximal number of user's answers
      success_min:
        minimal user's success rate
      success_max:
        maximal user's success rate
      variable_name:
        name of the filtered parameter
      variable_min:
        minimal value of the parameter of the model
      variable_max:
        maximal value of parameter of the model
      limit:
        number of returned questions (default 10, maximum 100)
    '''
    limit = int(request.GET.get('limit', 1))

    def _get_interval(key):
        return request.GET.get('{}_min'.format(key)), request.GET.get('{}_max'.format(key))

    def _convert_time_interval(interval):
        mapped = [None if x is None else datetime.datetime.strptime(x, '%Y-%m-%d') for x in list(interval)]
        return mapped[0], mapped[1]

    recommended = models_recommend_users(
        _convert_time_interval(_get_interval('register')),
        _get_interval('number_of_answers'),
        _get_interval('success'),
        request.GET.get('variable_name'),
        _get_interval('variable'),
        limit)
    return render_json(request, recommended, template='models_json.html', help_text=recommend_users.__doc__)


@allow_lazy_user
def audit(request, key):
    if 'user' in request.GET:
        user = get_user_id(request)
    else:
        user = None
    limit = 100
    if request.user.is_staff:
        limit = request.GET.get('limit', limit)
    item_identifier = request.GET['item'] if 'item' in request.GET else None
    item_secondary_identifier = request.GET['item_secondary'] if 'item_secondary' in request.GET else None
    translated = Item.objects.translate_identifiers([i for i in [item_identifier, item_secondary_identifier] if i is not None], get_language(request))
    item = translated.get(item_identifier)
    item_secondary = translated.get(item_secondary_identifier)
    time = get_time(request)
    environment = get_environment()
    if is_time_overridden(request):
        environment.shift_time(time)
    values = environment.audit(
        key, user=user, item=item, item_secondary=item_secondary, limit=limit)

    def _to_json_audit(audit):
        (time, value) = audit
        return {
            'object_type': 'value',
            'key': key,
            'item_primary_id': item,
            'item_secondary_id': item_secondary,
            'user_id': user,
            'value': value,
            'time': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    return render_json(request, list(map(_to_json_audit, values)), template='models_json.html')


@allow_lazy_user
def read(request, key):
    if 'user' in request.GET:
        user = get_user_id(request)
    else:
        user = None
    item = int(request.GET['item']) if 'item' in request.GET else None
    item_secondary = int(request.GET['item_secondary']) if 'item_secondary' in request.GET else None
    time = get_time(request)
    environment = get_environment()
    if is_time_overridden(request):
        environment.shift_time(time)
    value = environment.read(key, user=user, item=item, item_secondary=item_secondary)
    if value is None:
        return render_json(
            request,
            {'error': 'value with key "%s" not found' % key},
            template='models_json.html', status=404)
    else:
        return render_json(
            request,
            {
                'object_type': 'value',
                'key': key,
                'item_primary_id': item,
                'item_secondary_id': item_secondary,
                'user_id': user,
                'value': value
            },
            template='models_json.html'
        )


def _get_answers(request):
    data = json.loads(request.body.decode("utf-8"))
    if "answer" in data:
        answers = [data["answer"]]
    elif "answers" in data:
        answers = data["answers"]
    else:
        raise BadRequestException("Answer(s) not found")

    return answers


def _save_answers(request, practice_context, finish_practice_set):
    timer('_save_answers')
    json_objects = _get_answers(request)
    answers = []
    last_answers = Answer.objects.prefetch_related('practice_set').filter(user_id=request.user.id).order_by('-id')[:1]
    if len(last_answers) == 0 or last_answers[0].context_id != practice_context.id or last_answers[0].practice_set is None or last_answers[0].practice_set.finished:
        if len(last_answers) > 0 and last_answers[0].context_id != practice_context.id:
            PracticeSet.objects.filter(answer__user_id=request.user.id).update(finished=True)
        practice_set = PracticeSet.objects.create()
    else:
        practice_set = last_answers[0].practice_set
    if finish_practice_set:
        practice_set.finished = True
        practice_set.save()
    for json_object in json_objects:
        if 'answer_class' not in json_object:
            raise BadRequestException('The answer does not contain key "answer_class".')
        answer_class = Answer.objects.answer_class(json_object['answer_class'])
        answers.append(answer_class.objects.from_json(json_object, practice_context, practice_set, request.user.id))
    LOGGER.debug("saving of %s answers took %s seconds", len(answers), timer('_save_answers'))
    return answers
