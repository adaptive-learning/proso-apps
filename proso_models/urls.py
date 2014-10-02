from django.conf.urls import patterns, url

urlpatterns = patterns(
    'proso_models.views',
    url(r'^home', 'home', name='home'),
    url(r'^read/(?P<key>[\w_]+)', 'read', name='read'),
    url(r'^audit/(?P<key>[\w_]+)', 'audit', name='audit'),
    url(r'^model/', 'model', name='model'),
)
