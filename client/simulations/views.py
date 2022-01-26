from braces.views import UserFormKwargsMixin
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView
from files.models import CellmlModel, IonCurrent

from .forms import (
    CompoundConcentrationPointFormSet,
    IonCurrentFormSet,
    SimulationEditForm,
    SimulationForm,
)
from .models import Simulation, CompoundConcentrationPoint, SimulationIonCurrentParam


def to_int(f):
    """
    Convert to into only if it is an in else don't convert.
    """
    return int(f) if f.is_integer() else f


class SimulationListView(ListView):
    """
    List all user's Simulations
    """
    template_name = 'simulations/simulation_list.html'

    def get_queryset(self):
        return (sim for sim in Simulation.objects.all() if sim.is_visible_to(self.request.user))


class SimulationCreateView(LoginRequiredMixin, UserFormKwargsMixin, CreateView):
    """
    Create a new Simulation
    """
    model = Simulation
    form_class = SimulationForm
    ion_formset_class = IonCurrentFormSet
    concentration_formset_class = CompoundConcentrationPointFormSet
    template_name = 'simulations/simulation.html'

    def get_initial(self):
        #pk = self.kwargs.get('pk', None)
        if not self.pk:
            return None
        sim = Simulation.objects.get(pk=self.pk)
        return {'notes': sim.notes,
                'model': sim.model,
                'pacing_frequency': sim.pacing_frequency,
                'maximum_pacing_time': sim.maximum_pacing_time,
                'ion_current_type': sim.ion_current_type,
                'ion_units': sim.ion_units,
                'pk_or_concs': sim.pk_or_concs,
                'minimum_concentration': sim.minimum_concentration,
                'maximum_concentration': sim.maximum_concentration,
                'intermediate_point_count': sim.intermediate_point_count,
                'intermediate_point_log_scale': sim.intermediate_point_log_scale,
                'PK_data': sim.PK_data}

    def get_ion_formset(self):
        if not hasattr(self, 'ion_formset') or self.ion_formset is None:
            #pk = self.kwargs.get('pk', None)
            initial = []
            for curr in IonCurrent.objects.all():
                param = None
                if self.pk:
                  param = SimulationIonCurrentParam.objects.filter(simulation=Simulation.objects.get(pk=self.pk),
                                                                   current=curr.pk) if self.pk else None
                  if param.exists():
                      param = param.first()
                initial.append({'current': param.current if param else None,
                                'ion_current': curr,
                                'hill_coefficient': to_int(param.hill_coefficient if param else curr.default_hill_coefficient),
                                'saturation_level': to_int(param.saturation_level if param else curr.default_saturation_level),
                                'spread_of_uncertainty': param.spread_of_uncertainty if param else None,
                                'default_spread_of_uncertainty': to_int(param.spread_of_uncertainty if param else curr.default_spread_of_uncertainty),
                                'channel_protein': curr.channel_protein,
                                'gene': curr.gene, 'description': curr.description,
                                'models': [m.id for m in CellmlModel.objects.all()
                                           if curr in m.ion_currents.all() and m.is_visible_to(self.request.user)]})
            form_kwargs = {'user': self.request.user}
            self.ion_formset = self.ion_formset_class(self.request.POST or None, initial=initial, prefix='ion',
                                                      form_kwargs=form_kwargs)
        return self.ion_formset

    def get_concentration_formset(self):
        if not hasattr(self, 'concentration_formset') or self.concentration_formset is None:
            initial = []
            if self.pk:
                initial = CompoundConcentrationPoint.objects.filter(simulation=Simulation.objects.get(pk=self.pk)).values()
            form_kwargs = {'user': self.request.user}
            self.concentration_formset = self.concentration_formset_class(self.request.POST or None,
                                                                          prefix='concentration',
                                                                          initial=initial,
                                                                          form_kwargs=form_kwargs)
        return self.concentration_formset

    def get_context_data(self, **kwargs):
        self.pk = self.kwargs.get('pk', None)
        kwargs['ion_formset'] = self.get_ion_formset()
        kwargs['concentration_formset'] = self.get_concentration_formset()
        kwargs['template_title'] = Simulation.objects.get(pk=self.pk).title if self.pk else None
        return super().get_context_data(**kwargs)

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('simulations:simulation_list')

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


class SimulationEditView(LoginRequiredMixin, UserPassesTestMixin, UserFormKwargsMixin, UpdateView):
    """
    View for editing simulations.
    We can only edit title / description not other parameters.
    For other parameters, a new simulation would be needed.
    """
    model = Simulation
    form_class = SimulationEditForm
    template_name = 'simulations/simulation_edit.html'

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('simulations:simulation_list')

    def test_func(self):
        return self.get_object().is_editable_by(self.request.user)

class SimulationResultView(LoginRequiredMixin, UserPassesTestMixin, UserFormKwargsMixin, DetailView):
    """
    View viewing simulations details (and results).
    """
    model = Simulation
    template_name = 'simulations/simulation_result.html'

    def test_func(self):
        return self.get_object().is_editable_by(self.request.user)


class SimulationDeleteView(UserPassesTestMixin, DeleteView):
    """
    Delete a simulation
    """
    model = Simulation
    # Raise a 403 error rather than redirecting to login,
    # if the user doesn't have delete permissions.
    raise_exception = True

    def test_func(self):
        return self.get_object().is_editable_by(self.request.user)

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('simulations:simulation_list')
