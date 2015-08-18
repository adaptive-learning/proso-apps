from django.conf.urls import patterns, url
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

urlpatterns = patterns(
    'proso_models.views',
    url(r'^(|home)$', ensure_csrf_cookie(TemplateView.as_view(template_name="models_home.html")), name='home'),
    url(r'^read/(?P<key>[\w_]+)', 'read', name='read'),
    url(r'^audit/(?P<key>[\w_]+)', 'audit', name='audit'),
    url(r'^model/', 'model', name='model'),
    url(r'^status/', 'status', name='models_status'),
    url(r'^recommend_users/', 'recommend_users', name='models_recommend_user'),
    url(r'^learning_curve/', 'learning_curve', name='models_learning_curve'),
)
