from django.conf.urls import patterns, url
from django.views.generic import TemplateView

urlpatterns = patterns(
    'proso_common.views',
    url(r'^(|home)$', (TemplateView.as_view(template_name="common_home.html")), name='common_home'),
    url(r'^config/$', 'config', name='config'),
    url(r'^csv/$', 'csv', name='csv_list'),
    url(r'^csv/(?P<table_name>\w+)', 'csv', name='csv_table'),
    url(r'^analysis/$', 'analysis', name='analysis'),
    url(r'^analysis/(?P<app_name>\w+)$', 'analysis', name='analysis'),
    url(r'^config_bar/$', (TemplateView.as_view(template_name="common_config_bar.html")), name='config_bar'),
)
