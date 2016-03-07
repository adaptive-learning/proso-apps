from django.conf.urls import patterns, url
from .models import Experiment, PossibleValue, Variable, ExperimentSetup
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView


urlpatterns = patterns(
    'proso_configab.views',
    url(r'^(|home)$', ensure_csrf_cookie(TemplateView.as_view(template_name="configab_home.html")), name='proso_configab_home'),
    url(r'^experiments$', 'show_more', {'object_class': Experiment}, name='show_configab_experiments'),
    url(r'^experiment/(?P<id>\d+)', 'show_one', {'object_class': Experiment}, name='show_configab_experiment'),
    url(r'^experimentsetup/(?P<id>\d+)', 'show_one', {'object_class': ExperimentSetup}, name='show_configab_experiment_setup'),
    url(r'^value/(?P<id>\d+)', 'show_one', {'object_class': PossibleValue}, name='show_configab_possible_value'),
    url(r'^variable/(?P<id>\d+)', 'show_one', {'object_class': Variable}, name='show_configab_variable'),
)
