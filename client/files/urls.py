from django.conf.urls import re_path

from . import views


urlpatterns = [
    re_path(
        r'^models/$',
        views.CellmlModelListView.as_view(),
        name='model_list',
    ),

    re_path(
        r'^models/new/$',
        views.CellmlModelCreateView.as_view(),
        name='create_model',
    ),
    re_path(
        r'^models/(?P<pk>\d+)/edit/$',
        views.CellmlModelUpdateView.as_view(),
        name='edit_model',
    ),
    re_path(
        r'^models/(?P<pk>\d+)/$',
        views.CellmlModelDetailView.as_view(),
        name='model_detail',
    ),
    re_path(
        r'^models/(?P<pk>\d+)/delete/$',
        views.CellmlModelDeleteView.as_view(),
        name='delete_model',
    ),

]
app_name = 'files'
