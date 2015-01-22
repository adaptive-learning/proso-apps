from django.conf.urls import patterns, url
from models import Category, Flashcard

urlpatterns = patterns(
    'proso_flashcards.views',
    url(r'^home', 'home', name='home'),
    url(r'^category/(?P<id>\d+)', 'show_one', {'object_class': Category}, name='proso_flashcards_show_category'),
    url(r'^categories', 'show_more', {'object_class': Category}, name='proso_flashcards_show_categories'),
    url(r'^flashcard/(?P<id>\d+)', 'show_one', {'object_class': Flashcard}, name='proso_flashcards_show_flashcard'),
    url(r'^flashcards', 'show_more', {'object_class': Flashcard}, name='proso_flashcards_show_flashcards'),
)
