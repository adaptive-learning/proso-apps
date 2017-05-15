from django.conf.urls import patterns, url
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView
from .models import PracticeSet

urlpatterns = patterns(
    'proso_models.views',
    url(r'^(|home)$', ensure_csrf_cookie(TemplateView.as_view(template_name="models_home.html")), name='models_home'),
    url(r'^answer/$', 'answer', name='models_answer'),
    url(r'^answers/$', 'answers', name='models_answers'),
    url(r'^answers_per_month/$', 'answers_per_month', name='models_answers_per_month'),
    url(r'^practice_image/', 'practice_image', name='models_practice_image'),
    url(r'^practice_sets/', 'show_more', {'object_class': PracticeSet, 'should_cache': False}, name='show_models_practice_sets'),
    url(r'^practice_set/(?P<id>\d+)', 'show_one', {'object_class': PracticeSet}, name='show_models_practice_set'),
    url(r'^practice/', 'practice', name='models_practice'),
    url(r'^status/', 'status', name='models_status'),
    url(r'^to_practice/', 'to_practice', name='models_to_practice'),
    url(r'^to_practice_counts/', 'to_practice_counts', name='models_to_practice_counts'),
    url(r'^user_stats/', 'user_stats', name='models_user_stats'),
)
