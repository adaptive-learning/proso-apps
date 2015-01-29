from django.conf.urls import patterns, url

urlpatterns = patterns(
    'proso_user.views',
    url(r'^home', 'home', name='home'),
    url(r'^session/', 'session', name='session'),
)
