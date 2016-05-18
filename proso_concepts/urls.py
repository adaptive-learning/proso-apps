from django.conf.urls import patterns, url
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView
from proso_concepts.models import Tag, Concept

MODELS = [Tag, Concept]


urlpatterns = patterns('proso_concepts.views',
    url(r'^(|home)$', ensure_csrf_cookie(TemplateView.as_view(template_name="concepts_home.html")), name='home'),
    url(r'^user_stats$', "user_stats", name="user_stats"),
    url(r'^user_stats_bulk$', "user_stats_bulk", name="user_stats_bulk"),
    url(r'^(?P<provider>\w+)_user_stats', "user_stats_api", name="user_stats_api"),
    url(r'^tag_values$', "tag_values", name="tag_values"),
)


for model in MODELS:
    name = model.__name__.lower()
    urlpatterns += patterns('proso_concepts.views',
        url(r'^{}/(?P<id>\d+)$'.format(name), 'show_one', {'object_class': model}, name='show_{}'.format(name)),
        url(r'^{}s$'.format(name), 'show_more', {'object_class': model}, name='show_{}s'.format(name)),
    )
