import requests
from django.utils import timezone
from django.conf import settings
from braces.views import UserFormKwargsMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic.base import RedirectView
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
from .models import CompoundConcentrationPoint, Simulation, SimulationIonCurrentParam



PROGRESS_STATUS_CHOICES = {'Initialising..': 1,
                           '0% completed': 2,
                           '7% completed': 7,
                           '15% completed': 15,
                           '23% completed': 23,
                           '30% completed': 30,
                           '38% completed': 38,
                           '46% completed': 46,
                           '53% completed': 53,
                           '61% completed': 61,
                           '69% completed': 69,
                           '76% completed': 76,
                           '84% completed': 84,
                           '92% completed': 92,
                           'Finalising..': 95,
                           '100% completed': 99,
                           '..done!': 100}


def to_int(f):
    """
    Convert to into only if it is an in else don't convert.
    """
    return int(f) if f.is_integer() else f


def start_simulation(sim):
    """
    Makes the request to (re-)start the simulation if a simulation without ap_predict_call_id is saved.
    """
    #todo: ic50, ic50 units, concentration points, pk_data, cellml_file
    call_data = {'pacingFrequency': sim.pacing_frequency,
                 'pacingMaxTime': sim.maximum_pacing_time,
                 'plasmaMaximum': sim.maximum_concentration,
                 'plasmaMinimum': sim.minimum_concentration,
                 'plasmaIntermediatePointCount': sim.intermediate_point_count,
                 'plasmaIntermediatePointLogScale': sim.intermediate_point_log_scale}

    if sim.model.ap_predict_model_call:
        call_data['modelId'] = sim.model.ap_predict_model_call
    else:
#assert False, str(sim.model.cellml_file.url)
        call_data['modelId'] = sim.model.cellml_file.url

    for current_param in SimulationIonCurrentParam.objects.filter(simulation=sim):
        call_data[current_param.ion_current.name] = {
            'associatedData': [{sim.ion_current_type: current_param.current,
                                'hill': current_param.hill_coefficient,
                                'saturation': current_param.saturation_level}]
        }
        if current_param.spread_of_uncertainty:
            call_data[current_param.ion_current.name]['spreads'] = \
                {'c50Spread': current_param.spread_of_uncertainty}

    call_response = {}
    sim.ap_predict_last_called = timezone.now()
    try:
        response = requests.post(settings.AP_PREDICT_ENDPOINT, timeout=settings.AP_PREDICT_TIMEOUT, json=call_data)
        response.raise_for_status()  # Raise exception if request response doesn't return successful status
        call_response = response.json()
        sim.ap_predict_call_id = call_response['success']['id']
        sim.status = Simulation.Status.INITIALISING
    except requests.exceptions.RequestException as http_err:
        sim.status = Simulation.Status.FAILED
        sim.ap_predict_messages = 'Call to start sim failed: %s' % type(http_err)
    except KeyError:
        sim.status = Simulation.Status.FAILED
        sim.ap_predict_messages = call_response
    finally:
        sim.save()

def re_start_simulation(sim):
    # restart if it was a succesful run, or there is no new progress we missed
    if sim.progress = 100 or sim.progress == update_progress(sim):
        # try to stop simulation
        try:#can_restart template-tag
            response = requests.get(settings.AP_PREDICT_ENDPOINT + '/api/collection/%s/STOP' % sim.ap_predict_call_id,
                                    timeout=settings.AP_PREDICT_TIMEOUT)
        except requests.exceptions.RequestException as http_err:
            sim.ap_predict_messages = 'Call to stop sim failed: %s' % type(http_err)
        # restart simulation
        start_simulation(sim)

def update_progress(sim):
    if sim.ap_predict_call_id:  # can't update without call_id
        try:
            response = requests.get(settings.AP_PREDICT_ENDPOINT + '/api/collection/%s/messages' % sim.ap_predict_call_id,
                                    timeout=settings.AP_PREDICT_TIMEOUT)
            response.raise_for_status()  # Raise exception if request response doesn't return successful status
            call_response = response.json()
            if 'success' in call_response:
                sim.messages = call_response['success']
                progress_text = next((p for p in reversed(call_response['success']) if p), '')
                sim.progress = PROGRESS_STATUS_CHOICES.get(progress_text, 0)
                if sim.progress == 100:
                    sim.status = Simulation.Status.SUCCESS if sim.progress == 100 else Simulation.Status.RUNNING
        except requests.exceptions.RequestException as http_err:
            sim.status = Simulation.Status.FAILED
            sim.ap_predict_messages = 'Call to get progress failed: %s' % type(http_err)
        finally:
            sim.save()
        return sim.progress

class SimulationListView(LoginRequiredMixin, ListView):
    """
    List all user's Simulations
    """
    template_name = 'simulations/simulation_list.html'

    def get_queryset(self):
        return Simulation.objects.filter(author=self.request.user)


class SimulationCreateView(LoginRequiredMixin, UserFormKwargsMixin, CreateView):
    """
    Create a new Simulation
    """
    model = Simulation
    form_class = SimulationForm
    ion_formset_class = IonCurrentFormSet
    concentration_formset_class = CompoundConcentrationPointFormSet
    template_name = 'simulations/simulation.html'

    def dispatch(self, request, *args, **kwargs):
        # Save pk, incase we run as a template
        self.pk = kwargs.get('pk', None)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
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
            initial = []
            visible_models = (CellmlModel.objects.filter(predefined=True) |
                              CellmlModel.objects.filter(predefined=False,
                                                         author=self.request.user)).values_list('pk', flat=True)
            for curr in IonCurrent.objects.all():
                param = SimulationIonCurrentParam.objects.filter(simulation=self.pk, ion_current=curr).first()
                initial.append({'current': param.current if param else None,
                                'ion_current': curr,
                                'hill_coefficient': to_int(param.hill_coefficient if param
                                                           else curr.default_hill_coefficient),
                                'saturation_level': to_int(param.saturation_level if param
                                                           else curr.default_saturation_level),
                                'spread_of_uncertainty': param.spread_of_uncertainty if param else None,
                                'default_spread_of_uncertainty': to_int(param.spread_of_uncertainty if param
                                                                        else curr.default_spread_of_uncertainty),
                                'channel_protein': curr.channel_protein,
                                'gene': curr.gene, 'description': curr.description,
                                'models': CellmlModel.objects.filter(pk__in=visible_models,
                                                                     ion_currents__pk=curr.pk).values_list('pk',
                                                                                                           flat=True)})
            form_kwargs = {'user': self.request.user}
            self.ion_formset = self.ion_formset_class(self.request.POST or None, initial=initial, prefix='ion',
                                                      form_kwargs=form_kwargs)
        return self.ion_formset

    def get_concentration_formset(self):
        if not hasattr(self, 'concentration_formset') or self.concentration_formset is None:
            initial = CompoundConcentrationPoint.objects.filter(simulation=self.pk)
            form_kwargs = {'user': self.request.user}
            self.concentration_formset = self.concentration_formset_class(self.request.POST or None,
                                                                          prefix='concentration',
                                                                          initial=initial.values() if initial else [],
                                                                          form_kwargs=form_kwargs)
        return self.concentration_formset

    def get_context_data(self, **kwargs):
        kwargs['ion_formset'] = self.get_ion_formset()
        kwargs['concentration_formset'] = self.get_concentration_formset()
        if self.pk:
            title = Simulation.objects.get(pk=self.pk).title
            kwargs['template_title'] = title
            messages.add_message(self.request, messages.INFO,
                                 'Using existing simulation <em>%s</em> as a template.' % title)
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
            # kick off simulation (via signal)
            start_simulation(simulation)
            #simulation.save()
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
        return self.get_object().author == self.request.user


class SimulationResultView(LoginRequiredMixin, UserPassesTestMixin, UserFormKwargsMixin, DetailView):
    """
    View viewing simulations details (and results).
    """
    model = Simulation
    template_name = 'simulations/simulation_result.html'

    def test_func(self):
        return self.get_object().author == self.request.user


class SimulationDeleteView(UserPassesTestMixin, DeleteView):
    """
    Delete a simulation
    """
    model = Simulation
    # Raise a 403 error rather than redirecting to login,
    # if the user doesn't have delete permissions.
    raise_exception = True

    def test_func(self):
        return self.get_object().author == self.request.user

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('simulations:simulation_list')

class RestartSimulationView(LoginRequiredMixin, UserPassesTestMixin, UserFormKwargsMixin, RedirectView):
    """
    View restarting the simulation
    """
    model = Simulation

    def test_func(self):
        simulation_set = Simulation.objects.filter(pk=self.kwargs['pk'])
        return simulation_set.count() == 1 and simulation_set.first().author == self.request.user


    def get_redirect_url(self, *args, **kwargs):
        simulation = Simulation.objects.get(pk=self.kwargs['pk'])
        re_start_simulation(simulation)
        return self.request.META['HTTP_REFERER']

class StatusSimulationView(LoginRequiredMixin, UserPassesTestMixin, UserFormKwargsMixin, DetailView):
    """
    Update the status of the simulation
    """
    model = Simulation
    template_name = 'simulations/simulation_status.html'

    def test_func(self):
        update_progress(self.get_object())
        return self.get_object().author == self.request.user
