from braces.views import UserFormKwargsMixin
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView

from .forms import CellmlModelForm
from .models import CellmlModel


class CellmlModelView(LoginRequiredMixin, UserFormKwargsMixin, CreateView):
    model = CellmlModel
    form_class = CellmlModelForm
    template_name = 'files/cellmlmodel.html'
    success_url = reverse_lazy('home')


class CellmlModelListView(LoginRequiredMixin, ListView):
    """
    List all visible models
    """
    template_name = 'files/model_list.html'

    def get_queryset(self):
        return [model for model in CellmlModel.objects.all() if self.request.user in model.viewers]

class CellmlModelDetailView(UserPassesTestMixin, DetailView):
    model = CellmlModel
    template_name = 'files/cellmlmodel_detail.html'

    def test_func(self):
        self.object = self.get_object()
        return self.request.user in self.object.viewers

# edit view
# list view
# deploy
