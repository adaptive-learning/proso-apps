from django.conf.urls import patterns, url
from django.views.generic import TemplateView

urlpatterns = patterns(
    'proso_common.views',
    url(r'^(|home)$', (TemplateView.as_view(template_name="common_home.html")), name='common_home'),
    url(r'^config/$', 'config', name='config'),
    url(r'^custom_config/$', 'custom_config', name='custom_config'),
    url(r'^csv/$', 'csv', name='csv_list'),
    url(r'^csv/(?P<filename>\w+)', 'csv', name='csv_table'),
    url(r'^log/$', 'log', name='log'),
    url(r'^config_bar/$', (TemplateView.as_view(template_name="common_config_bar.html")), name='config_bar'),
    url(r'^languages/$', 'languages', name='languages'),
)
