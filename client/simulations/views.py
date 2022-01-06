from braces.views import UserFormKwargsMixin
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView

from files.models import CellmlModel, IonCurrent
from .models import Simulation, SimulationIonCurrentParam
from .forms import SimulationForm



class CellmlModelCreateView(LoginRequiredMixin, UserFormKwargsMixin, CreateView):
    """
    Create a new Simulation
    """
    model = Simulation
    form_class = SimulationForm
    template_name = 'simulations/simulation.html'
    success_url = reverse_lazy('files:model_list')
