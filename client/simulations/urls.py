from django.conf.urls import re_path

from . import views


urlpatterns = [
    re_path(
        r'^simulation/new/$',
        views.CellmlModelCreateView.as_view(),
        name='create_simulation',
    ),

]
app_name = 'simulations'
