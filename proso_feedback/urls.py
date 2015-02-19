from django.conf.urls import patterns, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    'proso_feedback.views',
    url(r'^home$', 'home', name='home'),
    url(r'^feedback$', 'feedback', name='feedback'),
    url(r'^rating$', 'rating', name='rating'),
)
