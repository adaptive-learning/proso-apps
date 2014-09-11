from django.conf.urls import patterns, url
from models import Experiment

urlpatterns = patterns(
    'proso_ab.views',
    url(r'^/', 'home', name='home'),
    url(r'^experiments', 'show_more', {'object_class': Experiment}, name='show_experiments'),
)
