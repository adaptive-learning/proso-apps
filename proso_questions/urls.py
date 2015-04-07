from django.conf.urls import patterns, url
from models import Question, Category, Set, Resource, Option, DecoratedAnswer
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

urlpatterns = patterns(
    'proso_questions.views',
    url(r'^(|home)$', ensure_csrf_cookie(TemplateView.as_view(template_name="questions_home.html")), name='home'),
    url(r'^question/(?P<id>\d+)', 'show_one', {'object_class': Question}, name='show_question'),
    url(r'^questions', 'show_more', {'object_class': Question}, name='show_questions'),
    url(r'^answer$', 'answer', name='answer'),
    url(r'^answer/(?P<id>\d+)', 'show_one', {'object_class': DecoratedAnswer}, name='show_answer'),
    url(r'^answers', 'show_more', {'object_class': DecoratedAnswer, 'should_cache': False}, name='show_answers'),
    url(r'^option/(?P<id>\d+)', 'show_one', {'object_class': Option}, name='show_option'),
    url(r'^options', 'show_more', {'object_class': Option}, name='show_options'),
    url(r'^resource/(?P<id>\d+)', 'show_one', {'object_class': Resource}, name='show_resource'),
    url(r'^resources', 'show_more', {'object_class': Resource}, name='show_resources'),
    url(r'^set/(?P<id>\d+)', 'show_one', {'object_class': Set}, name='show_set'),
    url(r'^sets', 'show_more', {'object_class': Set}, name='show_sets'),
    url(r'^category/(?P<id>\d+)', 'show_one', {'object_class': Category}, name='show_category'),
    url(r'^categories', 'show_more', {'object_class': Category}, name='show_categories'),
    url(r'^practice$', 'practice', name='practice'),
    url(r'^test$', 'test', name='test'),
    url(r'^test/evaluate/(?P<question_set_id>\d+)', 'test_evaluate', name='test_evaluate'),
)
