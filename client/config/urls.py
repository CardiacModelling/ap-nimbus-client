"""clientdirect URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import include, re_path
from django.contrib import admin
from django.views.generic import TemplateView


urlpatterns = [
    re_path(r'^$', TemplateView.as_view(template_name='index.html'), name="home"),
    re_path(r'^contact$', TemplateView.as_view(template_name='contact.html'), name="contact"),
    re_path(r'^privacy$', TemplateView.as_view(template_name='privacy.html'), name="privacy"),

    re_path(r'^admin/', admin.site.urls),
    re_path(r'^accounts/', include('accounts.urls', namespace='accounts')),
    re_path(r'^accounts/', include('django.contrib.auth.urls')),
    re_path(r'^files/', include('files.urls', namespace='files')),
    re_path(r'^simulations/', include('simulations.urls', namespace='simulations')),
]
