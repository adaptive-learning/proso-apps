from django.conf.urls import patterns, url

urlpatterns = patterns(
    'proso_common.views',
    url(r'^csv/$', 'csv', name='csv_list'),
    url(r'^csv/(?P<table_name>\w+)', 'csv', name='csv_table'),
)
