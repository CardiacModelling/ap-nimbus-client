from braces.views import UserFormKwargsMixin
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView

from .forms import CellmlModelForm
from .models import CellmlModel


class CellmlModelListView(LoginRequiredMixin, ListView):
    """
    List all visible CellML models
    """
    template_name = 'files/cellmlmodel_list.html'

    def get_queryset(self):
        return [model for model in CellmlModel.objects.all() if model.is_visible_to(self.request.user)]


class CellmlModelCreateView(LoginRequiredMixin, UserFormKwargsMixin, CreateView):
    """
    Create a new CellML model
    """
    model = CellmlModel
    form_class = CellmlModelForm
    template_name = 'files/cellmlmodel.html'
    success_url = reverse_lazy('files:model_list')


class CellmlModelUpdateView(LoginRequiredMixin, UserPassesTestMixin, UserFormKwargsMixin, UpdateView):
    """
    Update a CellML model
    """
    model = CellmlModel
    form_class = CellmlModelForm
    template_name = 'files/cellmlmodel.html'
    success_url = reverse_lazy('files:model_list')

    def test_func(self):
        return self.get_object().is_editable_by(self.request.user)


class CellmlModelDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    View a CellML model
    """
    model = CellmlModel
    template_name = 'files/cellmlmodel_detail.html'

    def test_func(self):
        return self.get_object().is_visible_to(self.request.user)


class CellmlModelDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Delete a CellML model
    """
    model = CellmlModel
    # Raise a 403 error rather than redirecting to login,
    # if the user doesn't have delete permissions.
    raise_exception = True

    def test_func(self):
        return self.get_object().is_editable_by(self.request.user)

    def get_success_url(self, *args, **kwargs):
        ns = self.request.resolver_match.namespace
        return reverse_lazy(ns + ':model_list')
