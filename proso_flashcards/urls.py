from django.conf import settings
from django.conf.urls import patterns, url
from django.db.models import Model
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView
from proso_flashcards.models import Term, Category, Context, Flashcard, FlashcardAnswer

MODELS = [Flashcard, Category, FlashcardAnswer]
MODELS.append(settings.PROSO_FLASHCARDS.get("term_extension", Term))
MODELS.append(settings.PROSO_FLASHCARDS.get("context_extension", Context))

SHOULD_NOT_CACHE = [FlashcardAnswer]

urlpatterns = patterns(
    'proso_flashcards.views',
    url(r'^(|home)$', ensure_csrf_cookie(TemplateView.as_view(template_name="flashcards_home.html")), name='home'),
    url(r'^answer/$', 'answer', name='flashcard_answer'),
    url(r'^practice/', 'practice', name='flashcard_practice'),
    url(r'^practice_image/', 'practice_image', name='flashcard_practice_image'),
    url(r'^user_stats/', 'user_stats', name='flashcard_user_stats'),
    url(r'^ngService/', ensure_csrf_cookie(TemplateView.as_view(template_name="practice_service.html")),
        name='practice_service'),
)

for model in MODELS:
    name = model.__name__.lower() if model.__bases__[0] == Model else model.__bases__[0].__name__.lower()
    urlpatterns += patterns(
        'proso_flashcards.views',
        url(r'^{}/(?P<id>\d+)$'.format(name), 'show_one', {'object_class': model}, name='show_fc_{}'.format(name)),
        url(r'^{}s$'.format(name), 'show_more', {'object_class': model, 'should_cache': model not in SHOULD_NOT_CACHE},
            name='show_fc_{}s'.format(name)),
    )
