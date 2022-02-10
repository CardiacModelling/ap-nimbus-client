from django.urls import re_path

from . import views


urlpatterns = [
    re_path(
        r'^$',
        views.SimulationListView.as_view(),
        name='simulation_list',
    ),


    re_path(
        r'^new$',
        views.SimulationCreateView.as_view(),
        name='create_simulation',
    ),

    re_path(
        r'^(?P<pk>\d+)/edit$',
        views.SimulationEditView.as_view(),
        name='simulation_edit',
    ),

    re_path(
        r'^(?P<pk>\d+)/template$',
        views.SimulationCreateView.as_view(),
        name='simulation_template',
    ),

    re_path(
        r'^(?P<pk>\d+)/result$',
        views.SimulationResultView.as_view(),
        name='simulation_result',
    ),

    re_path(
        r'^(?P<pk>\d+)/delete$',
        views.SimulationDeleteView.as_view(),
        name='simulation_delete',
    ),

    re_path(
        r'^(?P<pk>\d+)/restart$',
        views.RestartSimulationView.as_view(),
        name='simulation_restart',
    ),
    re_path(
        r'^(?P<pk>\d+)/status$',
        views.StatusSimulationView.as_view(),
        name='simulation_status',
    ),
]
app_name = 'simulations'
