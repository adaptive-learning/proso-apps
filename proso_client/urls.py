from django.conf.urls import patterns, include, url
from django.views.generic import RedirectView
from django.http import HttpResponse
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()
from sitemap import sitemaps


urlpatterns = patterns(
    '',
    url(r'^$', 'proso_client.views.home', name='home'),
    url(r'^(how-it-works|about|view/\w*|u/\w+|practice/\w*|test/)',
        'proso_client.views.home', name='home'),

    url(r'^media/(?P<path>image/.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT}),
    url(r'^questions/', include('proso_questions.urls')),
    url(r'^models/', include('proso_models.urls')),
    url(r'^ab/', include('proso_ab.urls')),

    url(r'', include('social_auth.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^convert/', include('lazysignup.urls')),

    url(r'^favicon\.ico$', RedirectView.as_view(url='static/img/favicon.png')),
    url(r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
    url(r'^robots\.txt$', lambda r: HttpResponse("User-agent: *\nDisallow: ", mimetype="text/plain")),
    url(r'^user/logout/$', 'proso_client.views.logout_view', name='logout'),
)
