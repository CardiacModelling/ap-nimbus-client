from django.conf.urls import re_path

from . import views


urlpatterns = [
    re_path(
        r'^models/new/$',
        views.CellmlModelView.as_view(),
        name='create_model',
    ),

]
app_name = 'files'