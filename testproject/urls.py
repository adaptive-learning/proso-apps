from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib import admin


admin.autodiscover()

urlpatterns = patterns(
    '',
    url(
        r'^media/(?P<path>image/.*)$',
        'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}
    ),
    url(r'^user/', include('proso_user.urls')),
    url(r'^models/', include('proso_models.urls')),
    url(r'^configab/', include('proso_configab.urls')),
    url(r'^common/', include('proso_common.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^convert/', include('lazysignup.urls')),
    url(r'^feedback/', include('proso_feedback.urls')),
    url(r'^flashcards/', include('proso_flashcards.urls')),
    url(r'^tasks/', include('proso_tasks.urls', namespace='tasks')),
    url(r'^concepts/', include('proso_concepts.urls', namespace='concepts')),
    url(r'^subscription/', include('proso_subscription.urls')),
    url(r'^gopay/', include('gopay_django_api.urls')),
    url('', include('social.apps.django_app.urls', namespace='social'))
)
