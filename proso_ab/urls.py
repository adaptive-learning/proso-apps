from django.conf.urls import patterns, url
from models import Experiment, Value

urlpatterns = patterns(
    'proso_ab.views',
    url(r'^home', 'home', name='home'),
    url(r'^experiments', 'show_more', {'object_class': Experiment}, name='show_experiments'),
    url(r'^experiment/(?P<id>\d+)', 'show_one', {'object_class': Experiment}, name='show_ab_experiment'),
    url(r'^value/(?P<id>\d+)', 'show_one', {'object_class': Value}, name='show_ab_value'),
    url(r'^profile', 'profile', name='show_ab_profile'),
)
