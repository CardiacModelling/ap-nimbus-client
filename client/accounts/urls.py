from django.conf.urls import re_path
from django.contrib.auth import views as auth_views

from . import views


urlpatterns = [
    re_path(
        r'^login/$',
        auth_views.LoginView.as_view(),
        name='login',
    ),

    re_path(
        r'^register/$',
        views.RegistrationView.as_view(),
        name='register',
    ),

    re_path(
        r'^myaccount/$',
        views.MyAccountView.as_view(),
        name='myaccount',
    ),

    re_path(
        r'^(?P<pk>\d+)/delete/$',
        views.UserDeleteView.as_view(),
        name='delete',
    ),

]
app_name = 'accounts'
