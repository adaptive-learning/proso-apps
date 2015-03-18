from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from proso_flashcards.models import Term

urlpatterns = patterns(
    'proso_flashcards.views',
    url(r'^(|home)$', TemplateView.as_view(template_name="flashcards_home.html"), name='home'),
    url(r'^term/(?P<id>\d+)$', 'show_one', {'object_class': Term}, name='show_term'),
    url(r'^terms$', 'show_more', {'object_class': Term}, name='show_terms'),
)
