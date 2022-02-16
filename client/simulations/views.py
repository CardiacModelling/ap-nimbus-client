from urllib.parse import urljoin
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
from django.views.generic import View
from files.models import CellmlModel, IonCurrent
from django.http import JsonResponse
import asyncio
import requests
import aiohttp
import xlsxwriter
import io
from asgiref.sync import sync_to_async, async_to_sync
from django.utils.decorators import classonlymethod
from django.http import HttpResponseNotFound, FileResponse
from django.contrib.auth.decorators import login_required
from json.decoder import JSONDecodeError

from .forms import (
    CompoundConcentrationPointFormSet,
    IonCurrentFormSet,
    SimulationEditForm,
    SimulationForm,
)
from .models import CompoundConcentrationPoint, Simulation, SimulationIonCurrentParam



AP_MANAGER_URL = urljoin(settings.AP_PREDICT_ENDPOINT, 'api/collection/%s/%s')


def to_int(f):
    """
    Convert to into only if it is an in else don't convert.
    """
    return int(f) if f.is_integer() else f


def start_simulation(sim):
    """
    Makes the request to start the simulation.
    """
    # (re)set status and result
    sim.status = Simulation.Status.NOT_STARTED
    sim.progress = 'Initialising..'
    sim.ap_predict_last_update = timezone.now()
    sim.ap_predict_call_id = ''
    sim.ap_predict_messages = ''
    sim.q_net = ''
    sim.voltage_traces = ''
    sim.voltage_results = ''

    # build json data for api call
    #todo: pk_data, cellml_file
    call_data = {'pacingFrequency': sim.pacing_frequency,
                 'pacingMaxTime': sim.maximum_pacing_time}

    if sim.pk_or_concs == Simulation.PkOptions.pharmacokinetics:
        pass #pkdata
    elif sim.pk_or_concs == Simulation.PkOptions.compound_concentration_points:
        call_data['plasmaPoints'] = [c.concentration for c in CompoundConcentrationPoint.objects.filter(simulation=sim)]
    else: # sim.pk_or_concs == Simulation.PkOptions.compound_concentration_range:
        call_data['plasmaMaximum'] = sim.maximum_concentration
        call_data['plasmaMinimum'] = sim.minimum_concentration
        call_data['plasmaIntermediatePointCount'] = sim.intermediate_point_count
        call_data['plasmaIntermediatePointLogScale'] = sim.intermediate_point_log_scale

    if sim.model.ap_predict_model_call:
        call_data['modelId'] = sim.model.ap_predict_model_call
    else:
        call_data['modelId'] = sim.model.cellml_file.url

    for current_param in SimulationIonCurrentParam.objects.filter(simulation=sim):
        call_data[current_param.ion_current.name] = {
            'associatedData': [{'pIC50': Simulation.conversion(sim.ion_units)(current_param.current),
                                'hill': current_param.hill_coefficient,
                                'saturation': current_param.saturation_level}]
        }
        if current_param.spread_of_uncertainty:
            call_data[current_param.ion_current.name]['spreads'] = \
                {'c50Spread': current_param.spread_of_uncertainty}

    # call api
    try:
        response = requests.post(settings.AP_PREDICT_ENDPOINT, timeout=settings.AP_PREDICT_TIMEOUT,
                                 json=call_data)
        response.raise_for_status()  # Raise exception if request response doesn't return successful status
        call_response = response.json()
        sim.ap_predict_call_id = call_response['success']['id']
        sim.status = Simulation.Status.INITIALISING
    except (JSONDecodeError, requests.exceptions.RequestException, KeyError) as e:
        sim.progress = 'Failed!'
        sim.status = Simulation.Status.FAILED
        sim.ap_predict_messages = 'Progress failed. %s : %s' % (type(e), str(e))
    finally:  # save
        sim.save()

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
            # kick off simulation
            start_simulation(simulation)
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
        return Simulation.objects.get(pk=self.kwargs['pk']).author == self.request.user

    def get_redirect_url(self, *args, **kwargs):
        simulation = Simulation.objects.get(pk=self.kwargs['pk'])
        start_simulation(simulation)
        return self.request.META['HTTP_REFERER']


class ExcelSimulationView(LoginRequiredMixin, UserPassesTestMixin, UserFormKwargsMixin, DetailView):
    """
    Download the data as Excel
    """
    model = Simulation

    def test_func(self):
        return Simulation.objects.get(pk=self.kwargs['pk']).author == self.request.user

    def get(self, request, *args, **kwargs):
        sim = self.get_object()
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer)

        # add input values
        input_values =  workbook.add_worksheet('Input Values')
        input_values.write(0, 0, 'Title')
        input_values.write(0, 1, sim.title)

        input_values.write(2, 0, 'Model')
        input_values.write(2, 1, str(sim.model))
        input_values.write(4, 1, 'Pacing')
        input_values.write(4, 2, 'Frequency')
        input_values.write(4, 3, sim.pacing_frequency)
        input_values.write(4, 4, 'Hz')
        input_values.write(5, 2, 'Max time')
        input_values.write(5, 3, sim.maximum_pacing_time)
        input_values.write(5, 4, 'mins')

        input_values.write(7, 0, 'Ion Channel Current Inhibitory Concentrations')
        input_values.write(7, 3, 'Hill Coefficient')
        input_values.write(7, 4, 'Saturation Level (%)')
        input_values.write(7, 5, 'Spread of Uncertainty')
        input_values.write(7, 6, 'Channel protein')
        input_values.write(7, 7, 'Gene')
        input_values.write(7, 8, 'Description')
        for i, current in enumerate(SimulationIonCurrentParam.objects.filter(simulation=sim)):
            input_values.write(i + 7, 0, current.ion_current.name)
            input_values.write(i + 7, 1, current.current)
            input_values.write(i + 7, 2, sim.ion_units)
            input_values.write(i + 7, 3, current.hill_coefficient)
            input_values.write(i + 7, 4, current.saturation_level)
            input_values.write(i + 7, 5, current.spread_of_uncertainty)
            input_values.write(i + 7, 6, current.ion_current.channel_protein.replace('<sub>', ''). replace('</sub>', ' '))
            input_values.write(i + 7, 7, current.ion_current.gene)
            input_values.write(i + 7, 8, current.ion_current.description)

#        if simulation.pk_or_concs == Simulation.PkOptions.compound_concentration_range:
#            simulation.minimum_concentration
#            simulation.maximum_concentration
#        elif simulation.pk_or_concs == Simulation.PkOptions.compound_concentration_points:
#            points = [p.concentration for p in CompoundConcentrationPoint.objects.filter(simulation=simulation)]
#            points_range = str(points) if len(points) <= 2 else '[' + str(points[0]) + ' ... ' + str(points[-1]) + ']'
#            return (str(points) + ' (µM)', points_range + ' (µM)')
#        else:
#            file_name = str(simulation.PK_data)
#            truncated = file_name[:20] + '...' if len(file_name) > 23 else file_name
#            return ('Compound concentrations from TSV file: %s.' % file_name, truncated)


        qNet = workbook.add_worksheet('% Change and qNet')
        voltage_traces =  workbook.add_worksheet('Voltage Traces')
        voltage_traces_plot =  workbook.add_worksheet('Voltage Traces (Plot format)')
        voltage_results =  workbook.add_worksheet('Voltage Results (Plot format)')

        workbook.close()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename='AP-Portal_%s.xlsx' % self.get_object().pk)

class StatusSimulationView(View):
    """
    View updating and retreiving simulation ststuses for a number of simulations
    Also stores data for any that have finished.
    Maes use of asyncio and aoihttp, to speed up making what could be many requests
    """

    COMMANDS = ('q_net', 'voltage_traces', 'voltage_results')

    class ApManagerTimeoutException(Exception):
        pass

    @classonlymethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view._is_coroutine = asyncio.coroutines._is_coroutine
        return view

    async def save_data(self, session, command, sim):
        async with session.get(AP_MANAGER_URL % (sim.ap_predict_call_id, command)) as res:
            response = await res.json(content_type=None)
            if 'success' in response:
                setattr(sim, command, response['success'])

    async def update_sim(self, session, sim):
        try:
            async with session.get(AP_MANAGER_URL % (sim.ap_predict_call_id, 'progress_status')) as res:
                response = await res.json(content_type=None)
                # get progress if there is progress
                progress_text = next((p for p in reversed(response.get('success', '')) if p), '')
                if progress_text and progress_text != sim.progress:  # if progress has changed, save it
                    sim.progress = progress_text
                    sim.status = Simulation.Status.RUNNING
                    if sim.progress == '..done!':
                        actions = [asyncio.ensure_future(self.save_data(session, command, sim)) for command in self.COMMANDS]
                        await asyncio.wait([asyncio.ensure_future(self.save_data(session, command, sim)) for command in self.COMMANDS])
                        sim.status = Simulation.Status.SUCCESS
                    sim.ap_predict_last_update = timezone.now()
                # handle timeout
                elif (timezone.now() - sim.ap_predict_last_update).total_seconds() > settings.AP_PREDICT_STATUS_TIMEOUT:
                    raise self.ApManagerCallTimeOut('Progress timeout, not changed in %s seconds.' % settings.AP_PREDICT_STATUS_TIMEOUT)
        except (JSONDecodeError, asyncio.TimeoutError, aiohttp.client_exceptions.ClientError, self.ApManagerException) as e:
            sim.progress = 'Failed!'
            sim.status = Simulation.Status.FAILED
            sim.ap_predict_messages = 'Progress failed. %s : %s' % (type(e), str(e))
        finally:  # save
            await sync_to_async(sim.save)()

    async def get(self, request, *args, **kwargs):
        authenticated, user_pk = await sync_to_async(lambda req: (req.user.is_authenticated, req.user.pk))(request)
        if not authenticated:  # user login is required
            return HttpResponseNotFound()

        pks = set(map(int, self.kwargs['pks'].strip('/').split('/')))
        # get simulations to get status for and the ones that need updating
        simulations = Simulation.objects.filter(author__pk=user_pk, pk__in=pks)
        sims_to_update = await sync_to_async(list)(simulations.exclude(status__in=(Simulation.Status.FAILED, Simulation.Status.SUCCESS)))

        if sims_to_update:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=settings.AP_PREDICT_TIMEOUT),
                                             raise_for_status=True) as session:
                await asyncio.wait([asyncio.ensure_future(self.update_sim(session, sim)) for sim in sims_to_update])

        # gather data for status responses
        data = await sync_to_async(lambda sims: [{'pk': sim.pk,
                                                  'progress': sim.progress,
                                                  'status': sim.status} for sim in sims])(simulations)
        return JsonResponse(data=data,
                            status=200, safe=False)
