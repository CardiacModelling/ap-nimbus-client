from braces.views import UserFormKwargsMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView
from django.urls import reverse_lazy

from .forms import CellmlModelForm
from .models import CellmlModel


class CellmlModelView(LoginRequiredMixin, UserFormKwargsMixin, CreateView):
    model = CellmlModel
    form_class = CellmlModelForm
    template_name = 'files/cellmlmodel.html'
    success_url = reverse_lazy('home')

# test non-admin user can't see predefined checkbox
# restrict upload to cellml
# edit view
# list view
# deploy
