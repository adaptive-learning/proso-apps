from django.conf.urls import patterns, url

urlpatterns = patterns(
    'proso_user.views',
    url(r'^home', 'home', name='home'),
    url(r'^login/', 'login', name='login'),
    url(r'^logout/', 'logout', name='logout'),
    url(r'^profile/', 'profile', name='profile'),
    url(r'^session/', 'session', name='session'),
    url(r'^signup/', 'signup', name='signup'),
)
