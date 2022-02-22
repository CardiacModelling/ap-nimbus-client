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
        r'^status(?P<pks>(/\d+){1,})(?:/)?$',
        views.StatusSimulationView.as_view(),
        name='simulation_status',
    ),
    re_path(
        r'^(?P<pk>\d+)/data$',
        views.DataSimulationView.as_view(),
        name='simulation_data',
    ),
    re_path(
        r'^(?P<pk>\d+)/spreadsheet$',
        views.SpreadsheetSimulationView.as_view(),
        name='simulation_spreadsheet',
    ),

]
app_name = 'simulations'
