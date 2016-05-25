from django.conf.urls import patterns, url
from django.db.models import Model
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView
from proso_tasks.models import Task, Context, TaskInstance, Skill

MODELS = [Task, TaskInstance, Context, Skill]

urlpatterns = patterns(
    'proso_tasks.views',
    url(r'^(|home)$', ensure_csrf_cookie(TemplateView.as_view(template_name="tasks_home.html")), name='home'),
)

for model in MODELS:
    name = model.__name__.lower() if model.__bases__[0] == Model else model.__bases__[0].__name__.lower()
    urlpatterns += patterns(
        'proso_tasks.views',
        url(r'^{}/(?P<id>\d+)$'.format(name), 'show_one', {'object_class': model}, name='show_{}'.format(name)),
        url(r'^{}s$'.format(name), 'show_more', {'object_class': model},
            name='show_{}s'.format(name)),
    )
