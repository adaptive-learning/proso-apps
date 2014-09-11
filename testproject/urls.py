from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib import admin

urlpatterns = patterns(
    '',
    url(r'^media/(?P<path>image/.*)$', 'django.views.static.serve', {
    'document_root': settings.MEDIA_ROOT}),
    url(r'^questions/', include('proso_questions.urls')),
    url(r'^models/', include('proso_models.urls')),
    url(r'^ab/', include('proso_ab.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
