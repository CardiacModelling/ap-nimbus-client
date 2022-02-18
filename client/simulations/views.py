import asyncio
import io
from itertools import zip_longest
from json.decoder import JSONDecodeError
from urllib.parse import urljoin

import aiohttp
import requests
import xlsxwriter
from asgiref.sync import sync_to_async
from braces.views import UserFormKwargsMixin
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import FileResponse, HttpResponseNotFound, JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import classonlymethod
from django.views.generic import View
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


def to_int(v):
    """
    Convert to into only if it is an in else don't convert.
    """
    return int(v) if v.is_integer() else v


def to_float(v):
    try:
        return float(v)
    except ValueError:
        return v


class ApManagerCallTimeOut(Exception):
    pass


class ApManagerCallStopped(Exception):
    pass


DONE = '..done!'
AP_MANAGER_URL = urljoin(settings.AP_PREDICT_ENDPOINT, 'api/collection/%s/%s')
API_EXCEPTIONS = (JSONDecodeError, KeyError, ApManagerCallTimeOut, ApManagerCallStopped, asyncio.TimeoutError,
                  aiohttp.client_exceptions.ClientError, requests.exceptions.RequestException)


def process_api_exception(e, when, response, sim):
    sim.progress = 'Failed!'
    sim.status = Simulation.Status.FAILED
    sim.api_errors = 'Simulation %s failed:\n' % when
    if 'error' in response:
        sim.api_errors += str(response['error']) + '\n'
    if isinstance(e, JSONDecodeError):
        sim.api_errors = 'API call %s returned invalid JSON.' % when
    elif isinstance(e, KeyError):
        sim.api_errors = 'API call %s returned unexpected JSON: %s' % (when, str(response))
    elif isinstance(e, ApManagerCallTimeOut):
        sim.api_errors = ('Progress timeout. Progress not changed for more than %s seconds.'
                          % settings.AP_PREDICT_STATUS_TIMEOUT)
    elif isinstance(e, ApManagerCallStopped):
        sim.api_errors = 'Simulation stopped prematurely.'
    else:
        sim.api_errors = 'API connection %s failed: %s' % (when, type(e))
    sim.api_errors = sim.api_errors[:254]  # truncate to make sure it fits


def start_simulation(sim):
    """
    Makes the request to start the simulation.
    """
    # (re)set status and result
    sim.status = Simulation.Status.NOT_STARTED
    sim.progress = 'Initialising..'
    sim.ap_predict_last_update = timezone.now()
    sim.ap_predict_call_id = ''
    sim.api_errors = ''
    sim.messages = ''
    sim.q_net = ''
    sim.voltage_traces = ''
    sim.voltage_results = ''

    # build json data for api call
    #todo: pk_data, cellml_file
    call_data = {'pacingFrequency': sim.pacing_frequency,
                 'pacingMaxTime': sim.maximum_pacing_time}

    if sim.pk_or_concs == Simulation.PkOptions.pharmacokinetics:
        assert False, "PK data not yet implemented" # pkdata
    elif sim.pk_or_concs == Simulation.PkOptions.compound_concentration_points:
        call_data['plasmaPoints'] = [c.concentration for c in CompoundConcentrationPoint.objects.filter(simulation=sim)]
    else:  # sim.pk_or_concs == Simulation.PkOptions.compound_concentration_range:
        call_data['plasmaMaximum'] = sim.maximum_concentration
        call_data['plasmaMinimum'] = sim.minimum_concentration
        call_data['plasmaIntermediatePointCount'] = sim.intermediate_point_count
        call_data['plasmaIntermediatePointLogScale'] = sim.intermediate_point_log_scale

    if sim.model.ap_predict_model_call:
        call_data['modelId'] = sim.model.ap_predict_model_call
    else:
        assert False, "uploaded cellml not yet implemented" #call_data['modelId'] = sim.model.cellml_file.url

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
    response = {}
    try:
        response = requests.post(settings.AP_PREDICT_ENDPOINT, timeout=settings.AP_PREDICT_TIMEOUT,
                                 json=call_data)
        response.raise_for_status()  # Raise exception if request response doesn't return successful status
        call_response = response.json()
        sim.ap_predict_call_id = call_response['success']['id']
        sim.status = Simulation.Status.INITIALISING
    except API_EXCEPTIONS as e:
        process_api_exception(e, 'start', response, sim)
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


class SpreadsheetSimulationView(LoginRequiredMixin, UserPassesTestMixin, UserFormKwargsMixin, DetailView):
    """
    Download the data as Spreadseet (.xlsx)
    """
    model = Simulation

    def test_func(self):
        return Simulation.objects.get(pk=self.kwargs['pk']).author == self.request.user

    def input_values(self, workbook, bold, sim):
        input_values = workbook.add_worksheet('Input Values')
        row = 0
        input_values.write(row, 0, 'Title', bold)
        input_values.write(row, 1, sim.title)
        row += 1

        input_values.write(row, 0, 'Created at', bold)
        input_values.write(row, 2, str(sim.created_at))
        row += 1

        input_values.write(row, 0, 'Created by', bold)
        input_values.write(row, 2, sim.author.full_name)
        row += 2

        input_values.write(row, 0, 'Model', bold)
        input_values.write(row, 1, str(sim.model))
        row += 2

        input_values.write(row, 1, 'Pacing', bold)
        input_values.write(row, 2, 'Frequency', bold)
        input_values.write(row, 3, sim.pacing_frequency)
        input_values.write(row, 4, 'Hz')
        row += 1

        input_values.write(row, 2, 'Max time', bold)
        input_values.write(row, 3, sim.maximum_pacing_time)
        input_values.write(row, 4, 'mins')
        row += 2

        input_values.write(row, 0, 'Ion Channel Current Inhibitory Concentrations', bold)
        input_values.write(row, 3, 'Hill Coefficient', bold)
        input_values.write(row, 4, 'Saturation Level (%)', bold)
        input_values.write(row, 5, 'Spread of Uncertainty', bold)
        input_values.write(row, 6, 'Channel protein', bold)
        input_values.write(row, 7, 'Gene', bold)
        input_values.write(row, 8, 'Description', bold)
        row += 1

        for current in SimulationIonCurrentParam.objects.filter(simulation=sim):
            input_values.write(row, 0, current.ion_current.name)
            input_values.write(row, 1, current.current)
            input_values.write(row, 2, sim.ion_units)
            input_values.write(row, 3, current.hill_coefficient)
            input_values.write(row, 4, current.saturation_level)
            input_values.write(row, 5, current.spread_of_uncertainty)
            input_values.write(row, 6, current.ion_current.channel_protein.replace('<sub>', ''). replace('</sub>', ' '))
            input_values.write(row, 7, current.ion_current.gene)
            input_values.write(row, 8, current.ion_current.description)
            row += 1

        row += 1
        if sim.pk_or_concs == Simulation.PkOptions.compound_concentration_range:
            input_values.write(row, 0, 'Compound Concentration Range', bold)
            input_values.write(row, 1, 'Minimum Concentration', bold)
            input_values.write(row, 2, sim.minimum_concentration)
            row += 1

            input_values.write(row, 1, 'Maximum Concentration', bold)
            input_values.write(row, 2, sim.maximum_concentration)
            row += 1

            input_values.write(row, 1, 'Intermediate Point Count', bold)
            input_values.write(row, 2, sim.intermediate_point_count)
            row += 1

            input_values.write(row, 1, 'Intermediate Point Log Scale', bold)
            input_values.write(row, 2, sim.intermediate_point_log_scale)
            row += 1
        elif sim.pk_or_concs == Simulation.PkOptions.compound_concentration_points:
            input_values.write(row, 0, 'Compound Concentration Points', bold)
            for point in CompoundConcentrationPoint.objects.filter(simulation=sim):
                input_values.write(row, 1, point.concentration)
                row += 1
        else:
            input_values.write(row, 0, 'PK data file', bold)
            input_values.write(row, 1, str(sim.PK_data))
            row += 1
        row += 1
        input_values.write(row, 0, 'Notes', bold)
        input_values.write(row, 1, sim.notes)

    def qNet(self, workbook, bold, sim):
        qNet = workbook.add_worksheet('% Change and qNet')
        row = 0
        qNet.write(row, 0, 'Concentration (µM)', bold)
        qNet.write(row, 1, 'Δ APD90 (%)', bold)
        qNet.write(row, 2, 'qNet (C/F)', bold)
        qNet.write(row, 3, 'PeakVm(mV)', bold)
        qNet.write(row, 4, 'UpstrokeVelocity(mV/ms)', bold)
        qNet.write(row, 5, 'APD50(ms)', bold)
        qNet.write(row, 6, 'APD90(ms)', bold)
        row += 1

        for v_res, qnet in zip_longest(sim.voltage_results[1:], sim.q_net):
            qNet.write(row, 0, to_float(v_res['c']))
            qNet.write(row, 1, to_float(v_res['da90'][0]) if len(v_res['da90']) == 1 else str(v_res['da90']))
            qNet.write(row, 2, to_float(qnet['qnet']) if qnet else 'n/a')
            qNet.write(row, 3, to_float(v_res['pv']))
            qNet.write(row, 4, to_float(v_res['uv']))
            qNet.write(row, 5, to_float(v_res['a50']))
            qNet.write(row, 6, to_float(v_res['a90']))
            row += 1

    def voltage_traces(self, workbook, bold, sim):
        voltage_traces = workbook.add_worksheet('Voltage Traces (concentration)')
        voltage_traces.write(1, 0, 'Time (ms)', bold)
        column = 0
        for trace in sim.voltage_traces:
            voltage_traces.write(0, column, 'Conc. %s µM' % trace['name'], bold)
            voltage_traces.write(1, column + 1, 'Membrane Voltage (mV)', bold)
            for i, series in enumerate(trace['series']):
                row = i + 2
                voltage_traces.write(row, column, to_float(series['name']))
                voltage_traces.write(row, column + 1, to_float(series['value']))
            column += 3

    def voltage_traces_plot(self, workbook, bold, sim):
        # gather and sort all the different timepoints used in any of the series
        # not all series uses every timepoint, so we need to know which ones exist in order for printing
        voltage_traces_plot = workbook.add_worksheet('Voltage Traces (Plot format)')
        voltage_traces_plot.write(0, 0, 'Time (ms)', bold)

        time_keys = set()
        for trace in sim.voltage_traces:
            for series in trace['series']:
                time_keys.add(to_float(series['name']))
        time_keys = sorted(time_keys)

        column = 1
        for trace in sim.voltage_traces:
            voltage_traces_plot.write(0, column, 'Conc. %s µM' % trace['name'], bold)
            column += 1

        for i, time in enumerate(time_keys):
            voltage_traces_plot.write(i + 1, 0, time)

        for i, trace in enumerate(sim.voltage_traces):
            column = i + 1
            for series in trace['series']:
                row = time_keys.index(to_float(series['name'])) + 1
                voltage_traces_plot.write(row, column, to_float(series['value']))

    def get(self, request, *args, **kwargs):
        sim = self.get_object()
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        bold = workbook.add_format({'bold': True})
        self.input_values(workbook, bold, sim)
        self.qNet(workbook, bold, sim)
        self.voltage_traces(workbook, bold, sim)
        self.voltage_traces_plot(workbook, bold, sim)

        workbook.close()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename='AP-Portal_%s.xlsx' % self.get_object().pk)


class StatusSimulationView(View):
    """
    View updating and retreiving simulation ststuses for a number of simulations
    Also stores data for any that have finished.
    Maes use of asyncio and aoihttp, to speed up making what could be many requests
    """

    COMMANDS = ('messages' 'q_net', 'voltage_traces', 'voltage_results')

    @classonlymethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view._is_coroutine = asyncio.coroutines._is_coroutine
        return view

    async def save_data(self, session, command, sim):
        try:
            async with session.get(AP_MANAGER_URL % (sim.ap_predict_call_id, command)) as res:
                response = await res.json(content_type=None)
                if 'success' in response:
                    setattr(sim, command, response['success'])
        except API_EXCEPTIONS as e:
            await sync_to_async(process_api_exception)(e, 'saving %s' % command, response, sim)

    async def update_sim(self, session, sim):
        response = {}
        try:
            async with session.get(AP_MANAGER_URL % (sim.ap_predict_call_id, 'progress_status')) as res:
                response = await res.json(content_type=None)
                # get progress if there is progress
                progress_text = next((p for p in reversed(response.get('success', '')) if p), '')
                progress_changed = progress_text and progress_text != sim.progress
                if progress_changed:  # if progress has changed, save it
                    sim.progress = progress_text
                    sim.status = Simulation.Status.RUNNING
                    sim.ap_predict_last_update = timezone.now()

                # handle timeout (no progress change within timeout interval, we're not done)
                if not progress_changed and progress_text != DONE and \
                        (timezone.now() -
                         sim.ap_predict_last_update).total_seconds() > settings.AP_PREDICT_STATUS_TIMEOUT:
                    raise ApManagerCallTimeOut()
                elif not progress_changed or progress_text == DONE:
                    # If there is no change, or if we are done see if we have stopped and try to save data
                    stop_response = {}
                    try:
                        # check if the simulation has stopped
                        async with session.get(AP_MANAGER_URL % (sim.ap_predict_call_id, 'STOP')) as res:
                            stop_response = await res.json(content_type=None)
                            if 'success' in stop_response and stop_response['success']:
                                # simulation has stopped, try to save results
                                await asyncio.wait([asyncio.ensure_future(self.save_data(session, command, sim))
                                                   for command in self.COMMANDS])
                                # check we have voltage_traces and haven't FAILED one of the save steps
                                if sim.voltage_traces and not sim.status == Simulation.Status.FAILED:
                                    sim.status = Simulation.Status.SUCCESS
                                    sim.progress = 'Completed'
                                else:  # saving results failed we must have stopped prematurely
                                    raise ApManagerCallStopped()
                    except API_EXCEPTIONS as e:
                        await sync_to_async(process_api_exception)(e, 'checking stop', stop_response, sim)
        except API_EXCEPTIONS as e:
            await sync_to_async(process_api_exception)(e, 'update progress', response, sim)
        finally:  # save
            await sync_to_async(sim.save)()

    async def get(self, request, *args, **kwargs):
        authenticated, user_pk = await sync_to_async(lambda req: (req.user.is_authenticated, req.user.pk))(request)
        if not authenticated:  # user login is required
            return HttpResponseNotFound()

        pks = set(map(int, self.kwargs['pks'].strip('/').split('/')))
        # get simulations to get status for and the ones that need updating
        simulations = Simulation.objects.filter(author__pk=user_pk, pk__in=pks)
        sims_to_update = await sync_to_async(list)(simulations.exclude(status__in=(Simulation.Status.FAILED,
                                                                                   Simulation.Status.SUCCESS)))

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
