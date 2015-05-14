from django.conf.urls import patterns, url
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    'proso_feedback.views',
    url(r'^(|home)$', ensure_csrf_cookie(TemplateView.as_view(template_name="feedback_home.html")), name='home'),
    url(r'^feedback/$', 'feedback', name='feedback'),
    url(r'^rating/$', 'rating', name='rating'),
)
