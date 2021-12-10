from django.conf.urls import re_path

from . import views


urlpatterns = [
    re_path(
        r'^model/$',
        views.ModelView.as_view(),
        name='login',
    ),

]
app_name = 'files'
