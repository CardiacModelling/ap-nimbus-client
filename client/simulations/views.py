from braces.views import UserFormKwargsMixin
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView

from files.models import CellmlModel, IonCurrent
from .models import Simulation, SimulationIonCurrentParam
from .forms import IonCurrentForm, IonCurrentFormSet, SimulationForm



class CellmlModelCreateView(LoginRequiredMixin, UserFormKwargsMixin, CreateView):
    """
    Create a new Simulation
    """
    model = Simulation
    form_class = SimulationForm
    formset_class = IonCurrentFormSet
    template_name = 'simulations/simulation.html'
    success_url = reverse_lazy('files:model_list')

    def get_formset(self):
        initial=[{'ion_current': c, 'hill_coefficient': c.default_hill_coefficient, 'saturation_level': c.default_saturation_level, 'spread_of_uncertainty': c.default_spread_of_uncertainty} for c in IonCurrent.objects.all()]
        if not hasattr(self, 'formset') or self.formset is None:
            form_kwargs = {'user': self.request.user}
            if self.request.method == 'POST':
                self.formset = self.formset_class(
                    self.request.POST,
                    initial=initial,
                    context=context,
                    form_kwargs=form_kwargs)
            else:
                self.formset = self.formset_class(initial=initial, form_kwargs=form_kwargs)
        return self.formset

    def get_context_data(self, **kwargs):
        kwargs['formset'] = self.get_formset()
        return super().get_context_data(**kwargs)
