from django.conf.urls import patterns, url
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView
from .models import UserQuestion, UserQuestionPossibleAnswer


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
    url(r'answer_question', 'answer_question', name='answer_question'),
    url(r'^questions_to_ask', 'questions_to_ask', name='user_questions_to_ask'),
    url(r'^questions/', 'show_more', {'object_class': UserQuestion}, name='show_user_questions'),
    url(r'^question/(?P<id>\d+)', 'show_one', {'object_class': UserQuestion}, name='show_user_question'),
    url(r'^possible_answers/', 'show_more', {'object_class': UserQuestionPossibleAnswer}, name='show_user_question_possible_answers'),
    url(r'^possible_answer/(?P<id>\d+)', 'show_one', {'object_class': UserQuestionPossibleAnswer}, name='show_user_question_possible_answer'),
    url(r'^stop_sending_emails/(?P<user_id>\d+)/(?P<token>\w+)', 'stop_sending_emails', name='user_stop_sending_emails'),
) + patterns(
    'proso_user.views_classes',
    url(r'^classes/$', 'classes', name='classes'),
    url(r'^create_class/$', 'create_class', name='create_class'),
    url(r'^join_class/$', 'join_class', name='join_class'),
    url(r'^create_student/$', 'create_student', name='create_student'),
    url(r'^login_student/$', 'login_student', name='login_student'),
)
