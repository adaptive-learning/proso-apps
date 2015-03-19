from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from proso_flashcards.models import Term, Category, Context, Flashcard

MODELS = [Term, Flashcard, Context, Category]

urlpatterns = patterns(
    'proso_flashcards.views',
    url(r'^(|home)$', TemplateView.as_view(template_name="flashcards_home.html"), name='home'),
)

for model in MODELS:
    name = model.__name__.lower()
    urlpatterns += patterns(
        'proso_flashcards.views',
        url(r'^{}/(?P<id>\d+)$'.format(name), 'show_one', {'object_class': model}, name='show_{}'.format(name)),
        url(r'^{}s$'.format(name), 'show_more', {'object_class': model}, name='show_{}s'.format(name)),
    )
