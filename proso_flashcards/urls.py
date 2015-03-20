from django.conf import settings
from django.conf.urls import patterns, url
from django.db.models import Model
from django.views.generic import TemplateView
from proso_flashcards.models import Term, Category, Context, Flashcard

MODELS = [Flashcard, Category]
MODELS.append(settings.PROSO_FLASHCARDS["term_extension"] if "term_extension" in settings.PROSO_FLASHCARDS else Term)
MODELS.append(
    settings.PROSO_FLASHCARDS["context_extension"] if "context_extension" in settings.PROSO_FLASHCARDS else Context)

urlpatterns = patterns(
    'proso_flashcards.views',
    url(r'^(|home)$', TemplateView.as_view(template_name="flashcards_home.html"), name='home'),
)

for model in MODELS:
    name = model.__name__.lower() if model.__bases__[0] == Model else model.__bases__[0].__name__.lower()
    urlpatterns += patterns(
        'proso_flashcards.views',
        url(r'^{}/(?P<id>\d+)$'.format(name), 'show_one', {'object_class': model}, name='show_{}'.format(name)),
        url(r'^{}s$'.format(name), 'show_more', {'object_class': model}, name='show_{}s'.format(name)),
    )
