from django.conf.urls import patterns, url
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView


urlpatterns = patterns(
    'proso_user.views',
    url(r'^(|home)$', ensure_csrf_cookie(TemplateView.as_view(template_name="user_home.html")), name='home'),
    url(r'^login/', 'login', name='login'),
    url(r'^logout/', 'logout', name='logout'),
    url(r'^profile/', 'profile', name='profile'),
    url(r'^session/', 'session', name='session'),
    url(r'^signup/', 'signup', name='signup'),
    url(r'^ngservice/', 'user_service', name='user_service'),
    url(r'^ngservice_test/', TemplateView.as_view(template_name="user_service_test.html"), name='user_service_test'),
    url(r'^close_popup/', TemplateView.as_view(template_name="close_popup.html"), name='close_popup'),
    url(r'^initmobile/', 'initmobile_view', name='initmobile'),
)
