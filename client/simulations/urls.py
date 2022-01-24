from django.conf.urls import re_path

from . import views


urlpatterns = [
    re_path(
        r'^$',
        views.SimulationListView.as_view(),
        name='simulation_list',
    ),


    re_path(
        r'^new/$',
        views.CellmlModelCreateView.as_view(),
        name='create_simulation',
    ),

    re_path(
        r'^(?P<pk>\d+)/edit$',
        views.SimulationEditView.as_view(),
        name='simulation_edit',
    ),

    re_path(
        r'^(?P<pk>\d+)/template$',
        views.CellmlModelCreateView.as_view(),
        name='simulation_template',
    ),

    re_path(
        r'^(?P<pk>\d+)/delete$',
        views.SimulationDeleteView.as_view(),
        name='simulation_delete',
    ),
]
app_name = 'simulations'
