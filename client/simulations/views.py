from braces.views import UserFormKwargsMixin
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView
from files.models import CellmlModel, IonCurrent

from .forms import CompoundConcentrationPointsFormSet, IonCurrentFormSet, SimulationForm
from .models import Simulation



def to_int(f):
    return int(f) if f.is_integer() else f


class CellmlModelCreateView(LoginRequiredMixin, UserFormKwargsMixin, CreateView):
    """
    Create a new Simulation
    """
    model = Simulation
    form_class = SimulationForm
    ion_formset_class = IonCurrentFormSet
    concentration_formset_class = CompoundConcentrationPointsFormSet
    template_name = 'simulations/simulation.html'

    def get_ion_formset(self):
        if not hasattr(self, 'ion_formset') or self.ion_formset is None:
            initial = [{'ion_current': c, 'hill_coefficient': to_int(c.default_hill_coefficient),
                        'saturation_level': to_int(c.default_saturation_level),
                        'spread_of_uncertainty': None,
                        'default_spread_of_uncertainty': to_int(c.default_spread_of_uncertainty),
                        'channel_protein': c.channel_protein,
                        'gene': c.gene, 'description': c.description,
                        'models': [m.id for m in CellmlModel.objects.all()
                                   if c in m.ion_currents.all() and m.is_visible_to(self.request.user)]}
                       for c in IonCurrent.objects.all()]
            form_kwargs = {'user': self.request.user}
            self.ion_formset = self.ion_formset_class(self.request.POST or None, initial=initial, prefix='ion',
                                                      form_kwargs=form_kwargs)
        return self.ion_formset

    def get_concentration_formset(self):
        if not hasattr(self, 'concentration_formset') or self.concentration_formset is None:
            form_kwargs = {'user': self.request.user}
            self.concentration_formset = self.concentration_formset_class(self.request.POST or None, prefix='concentration', form_kwargs=form_kwargs)
        return self.concentration_formset


    def get_context_data(self, **kwargs):
        kwargs['ion_formset'] = self.get_ion_formset()
        kwargs['concentration_formset'] = self.get_concentration_formset()
        return super().get_context_data(**kwargs)

    def get_success_url(self, *args, **kwargs):
        #ns = self.request.resolver_match.namespace
        #return reverse_lazy(ns + ':model_list')
        return reverse_lazy('files:model_list')

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        ion_formset = self.get_ion_formset()
        concentration_formset = self.get_concentration_formset()
        if form.is_valid() and ion_formset.is_valid() and concentration_formset.is_valid():
            simulation = form.save()
            ion_formset.save(simulation=simulation)
            concentration_formset.save(simulation=simulation)
            return self.form_valid(form)
        else:
            self.object = getattr(self, 'object', None)
            return self.form_invalid(form)
