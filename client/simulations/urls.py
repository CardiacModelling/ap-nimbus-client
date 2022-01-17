from django.conf.urls import re_path

from . import views


urlpatterns = [
    re_path(
        r'^simulation/new/$',
        views.CellmlModelCreateView.as_view(),
        name='create_simulation',
    ),
    
    url(
        r'^(?P<pk>\d+)/delete$',
        views.SimulationDeleteView.as_view(),
        name='simulation_delete',
    ),
]
app_name = 'simulations'
