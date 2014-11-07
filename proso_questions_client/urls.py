from django.conf.urls import patterns, url
from django.views.generic import RedirectView
from django.http import HttpResponse

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()
from sitemap import sitemaps


urlpatterns = patterns(
    '',
    url(r'^$', 'proso_questions_client.views.home', name='home'),
    url(r'^(how-it-works|about|view/\w*|u/\w+|practice/\w*|test/)',
        'proso_questions_client.views.home', name='home'),

    url(r'^favicon\.ico$', RedirectView.as_view(url='static/dist/favicon.png')),
    url(r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
    url(r'^robots\.txt$', lambda r: HttpResponse("User-agent: *\nDisallow: ", mimetype="text/plain")),
    url(r'^user/logout/$', 'proso_questions_client.views.logout_view', name='logout'),
    url(r'^feedback/', 'proso_questions_client.views.feedback', name='feedback'),
)
