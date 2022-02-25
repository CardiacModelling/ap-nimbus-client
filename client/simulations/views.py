import asyncio
import io
from itertools import zip_longest
from json.decoder import JSONDecodeError
from urllib.parse import urljoin

import aiohttp
import xlsxwriter
from asgiref.sync import async_to_sync, sync_to_async
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
import jsonschema

from .forms import (
    CompoundConcentrationPointFormSet,
    IonCurrentFormSet,
    SimulationEditForm,
    SimulationForm,
)
from .models import CompoundConcentrationPoint, Simulation, SimulationIonCurrentParam


DONE = '..done!'
AP_MANAGER_URL = urljoin(settings.AP_PREDICT_ENDPOINT, 'api/collection/%s/%s')
JSON_SCHEMAS = {
    'q_net': {'type': 'array',
              'items': {'type': 'object',
                        'properties': {'c': {'type': 'string'}, 'qnet': {'type': 'string'}},
                        'required': ['c', 'qnet'],
                        'additionalProperties': False}},

    'voltage_traces': {'type': 'array',
                       'items': {'type': 'object',
                                 'properties': {'name': {'type': 'string'},
                                                'series': {'type': 'array',
                                                           'items': {'type': 'object',
                                                                     'properties': {'name': {'type': 'number'},
                                                                                    'value': {'type': 'number'}},
                                                                     'required': ['name', 'value'],
                                                                     'additionalProperties': False}}},
                                 'required': ['name', 'series'],
                                 'additionalProperties': False}},

    'voltage_results': {'type': 'array',
                        'items': {'type': 'object',
                                  'properties': {'c': {'type': 'string'},
                                                 'pv': {'type': 'string'},
                                                 'uv': {'type': 'string'},
                                                 'a50': {'type': 'string'},
                                                 'a90': {'type': 'string'},
                                                 'da90': {'type': 'array',
                                                          'items': {'type': 'string'}}},
                                  'additionalProperties': False}}
}


def to_int(v: str):
    """
    Convert to into only if it is an int else don't convert.
    """
    return int(v) if v.is_integer() else v


def to_float(v):
    """
    Convert to float only if possible.
    """
    try:
        return float(v)
    except ValueError:
        return v


async def save_api_error(sim, message):
    """
    Set status and progress to Failed and save error message
    """
    sim.progress = 'Failed!'
    sim.status = Simulation.Status.FAILED
    sim.api_errors = message[:254]
    await sync_to_async(sim.save)()

async def get_from_api(session, call, sim):
    """
    Get the result of an API call
    """
    response = {}
    try:
        async with session.get(AP_MANAGER_URL % (sim.ap_predict_call_id, call)) as res:
            response = await res.json(content_type=None)
            if 'error' in response:
                await save_api_error(sim, f"API error message: {str(response['error'])}")
    except JSONDecodeError:
        await save_api_error(sim, f'Simulation failed:\n API call: {call} returned invalid JSON.')
    except aiohttp.ClientError as e:
        await save_api_error(sim, f'API connection failed for call: {call}: {str(e)}')
    except asyncio.TimeoutError:
        await save_api_error(sim, f'API connection timeput for call: {call}')
    except AssertionError as e:
        await save_api_error(sim, f'Something went wrong with API call {AP_MANAGER_URL % (sim.ap_predict_call_id, call)} check the URL is valid.')
    finally:
        try:  # validate a succesful result if we have a schema for it
            if 'success' in response and call in JSON_SCHEMAS:
                jsonschema.validate(instance=response['success'], schema=JSON_SCHEMAS[call])
        except jsonschema.exceptions.ValidationError as e:
            await save_api_error(sim, f'Result to call {call} failed JSON validation: {e.message}')
        finally:
            return response


async def start_simulation_call(json_data, sim):
    """
    Call to start simulation
    """
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=settings.AP_PREDICT_TIMEOUT),
                                         raise_for_status=True) as session:
            async with session.post(settings.AP_PREDICT_ENDPOINT, json=json_data) as res:
                response = await res.json(content_type=None)
                if 'error' in response:
                    await save_api_error(sim, f"API error message: {str(response['error'])}")
                else:
                    sim.ap_predict_call_id = response['success']['id']
                    sim.status = Simulation.Status.INITIALISING
                    await sync_to_async(sim.save)()
    except KeyError:
        await save_api_error(sim, 'Response to simulation start call diid not contain the simulation id.')
    except JSONDecodeError:
        await save_api_error(sim, 'Simulation failed:\n API call: start simulation returned invalid JSON.')
    except aiohttp.ClientError as e:
        await save_api_error(sim, f'API connection failed for call: start simulation: {str(e)}')
    except asyncio.TimeoutError:
        await save_api_error(sim, 'API connection timeput for call: start simulation')
    except AssertionError:
        await save_api_error(sim, f'Something went wrong with API call for {settings.AP_PREDICT_ENDPOINT} check the URL is valid.')

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
    async_to_sync(start_simulation_call)(call_data, sim)


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
                                'spread_of_uncertainty': param.spread_of_uncertainty
                                if param and param.spread_of_uncertainty
                                else None,
                                'default_spread_of_uncertainty': to_int(param.spread_of_uncertainty
                                                                        if param and param.spread_of_uncertainty
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
        if len(sim.voltage_results) > 0 and len(sim.voltage_results[0]['da90']) > 1:
            qNet.write(row, 1, ", ".join(sim.voltage_results[0]['da90']), bold)
            row += 1

        for v_res, qnet in zip_longest(sim.voltage_results[1:], sim.q_net):
            qNet.write(row, 0, to_float(v_res['c']))
            da90 = to_float(v_res['da90'][0]) if len(v_res['da90']) == 1 else ", ".join(v_res['da90'])
            qNet.write(row, 1, to_float(da90))
            qNet.write(row, 2, to_float(qnet['qnet']) if qnet else 'n/a')
            qNet.write(row, 3, to_float(v_res['pv']))
            qNet.write(row, 4, to_float(v_res['uv']))
            qNet.write(row, 5, to_float(v_res['a50']))
            qNet.write(row, 6, to_float(v_res['a90']))
            row += 1

    def voltage_traces(self, workbook, bold, sim):
        voltage_traces = workbook.add_worksheet('Voltage Traces (concentration)')
        column = 0
        for trace in sim.voltage_traces:
            voltage_traces.write(0, column, 'Conc. %s µM' % trace['name'], bold)
            voltage_traces.write(1, column, 'Time (ms)', bold)
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

    COMMANDS = ('q_net', 'voltage_traces', 'voltage_results', 'messages')

    @classonlymethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view._is_coroutine = asyncio.coroutines._is_coroutine
        return view

    async def save_data(self, session, command, sim):
        response = await get_from_api(session, command, sim)
        if response and 'success' in response:
            setattr(sim, command, response['success'])

    async def update_sim(self, session, sim):
        response = await get_from_api(session, 'progress_status', sim)
        # get progress if there is progress
        progress_text = next((p for p in reversed(response.get('success', '')) if p), '')
        progress_changed = progress_text and progress_text != sim.progress
        if progress_changed:  # if progress has changed, save it
            sim.progress = progress_text
            sim.status = Simulation.Status.RUNNING
            sim.ap_predict_last_update = timezone.now()

        # handle timeout (no progress change within timeout interval, and we're not done)
        if not progress_changed and progress_text != DONE and \
                (timezone.now() -
                 sim.ap_predict_last_update).total_seconds() > settings.AP_PREDICT_STATUS_TIMEOUT:
            sim.api_errors = ('Progress timeout. Progress not changed for more than '
                              f'{settings.AP_PREDICT_STATUS_TIMEOUT} seconds.')
        elif not progress_changed or progress_text == DONE:
            # If there is no change, or if we are done see if we have stopped and try to save data
            # check if the simulation has stopped
            stop_response = await get_from_api(session, 'STOP', sim)
            if stop_response and 'success' in stop_response and stop_response['success']:
                # simulation has stopped, try to save results
                await asyncio.wait([asyncio.ensure_future(self.save_data(session, command, sim))
                                    for command in self.COMMANDS])

                if sim.status != Simulation.Status.FAILED:  # if we didn't fail saving
                    # check we have voltage_traces
                    if sim.voltage_traces and sim.status != Simulation.Status.FAILED:
                        sim.status = Simulation.Status.SUCCESS
                        sim.progress = 'Completed'
                    else:  # we didn't get any data after stopping, we must have stopped prematurely
                        await save_api_error(sim, 'Simulation stopped prematurely. (No data available after simulation stopped).')
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


class DataSimulationView(LoginRequiredMixin, UserPassesTestMixin, UserFormKwargsMixin, DetailView):

    """
    Retreives the data for rendering the graphs.
    """
    model = Simulation

    def test_func(self):
        return self.get_object().author == self.request.user

    def get(self, request, *args, **kwargs):
        sim = self.get_object()
        data = {'adp90': [], #[{'label': f'Simulation @ {sim.pacing_frequency} Hz', 'data': [], 'lines': {'show': True, 'lineWidth': 2}, 'points': {'show': True}, 'color': 0}],
                'qnet': [{'label': f'Simulation @ {sim.pacing_frequency} Hz', 'data': [], 'lines': {'show': True, 'lineWidth': 2}, 'points': {'show': True}, 'color': 0}],
                'traces': []}


        appredict_data = {"dAp95%low": [["0", "0"], ["0.001", "0.00770995"], ["0.00359381", "0.042562"], ["0.0129155", "0.16749"], ["0.0464159", "0.612315"], ["0.16681", "2.15927"], ["0.599484", "7.35177"], ["2.15443", "22.9826"], ["7.74264", "58.7797"], ["27.8256", "118.427"], ["100", "289.79"]],
                          "dAp86%low": [["0", "0"], ["0.001", "0.0157343"], ["0.00359381", "0.0713579"], ["0.0129155", "0.270435"], ["0.0464159", "0.9754"], ["0.16681", "3.38084"], ["0.599484", "11.3279"], ["2.15443", "33.3663"], ["7.74264", "77.7503"], ["27.8256", "151.197"], ["100", "305.124"]],
                          "dAp68%low": [["0", "0"], ["0.001", "0.0255675"], ["0.00359381", "0.106618"], ["0.0129155", "0.396152"], ["0.0464159", "1.41462"], ["0.16681", "4.87728"], ["0.599484", "15.8733"], ["2.15443", "44.002"], ["7.74264", "95.2433"], ["27.8256", "286.463"], ["100", "590.076"]],
                          "dAp38%low": [["0", "0"], ["0.001", "0.0389059"], ["0.00359381", "0.154402"], ["0.0129155", "0.565929"], ["0.0464159", "2.00059"], ["0.16681", "6.83643"], ["0.599484", "21.5258"], ["2.15443", "55.8853"], ["7.74264", "113.92"], ["27.8256", "289.04"], ["100", "590.076"]],
                          'median_delta_APD90': [["0", "0"], ["0.001", "0.193572"], ["0.00359381", "0.369733"], ["0.0129155", "0.926583"], ["0.0464159", "2.87476"], ["0.16681", "9.38945"], ["0.599484", "28.1848"], ["2.15443", "68.3706"], ["7.74264", "133.729"], ["27.8256", "295.328"], ["100", "738.545"]],
                          "dAp38%upp": [["0", "0"], ["0.001", "0.0791883"], ["0.00359381", "0.298385"], ["0.0129155", "1.07345"], ["0.0464159", "3.7046"], ["0.16681", "12.3575"], ["0.599484", "35.9032"], ["2.15443", "82.0441"], ["7.74264", "160.77"], ["27.8256", "311.102"], ["100", "590.076"]],
                          "dAp68%upp": [["0", "0"], ["0.001", "0.120022"], ["0.00359381", "0.443844"], ["0.0129155", "1.58005"], ["0.0464159", "5.43954"], ["0.16681", "17.507"], ["0.599484", "47.5968"], ["2.15443", "100.925"], ["7.74264", "288.729"], ["27.8256", "590.076"], ["100", "590.076"]],
                          "dAp86%upp": [["0", "0"], ["0.001", "0.193089"], ["0.00359381", "0.702892"], ["0.0129155", "2.46739"], ["0.0464159", "8.35349"], ["0.16681", "25.737"], ["0.599484", "64.0622"], ["2.15443", "126.826"], ["7.74264", "297.717"], ["27.8256", "590.076"], ["100", "590.076"]],
                          "dAp95%upp": [["0", "0"], ["0.001", "0.282334"], ["0.00359381", "1.01717"], ["0.0129155", "3.51908"], ["0.0464159", "11.7705"], ["0.16681", "34.4422"], ["0.599484", "79.6112"], ["2.15443", "155.163"], ["7.74264", "307.66"], ["27.8256", "590.076"], ["100", "590.076"]]}

        dataset2 = [{'label': f'Simulation @ {sim.pacing_frequency} Hz', 'data': appredict_data["median_delta_APD90"], 'lines': { 'show': True }, 'points': {'show': True}, 'color': "#edc240" },
                    {'id': "dAp95%low", 'data': appredict_data["dAp95%low"], 'lines': {'show': True, 'lineWidth': 0, 'fill': False }, 'color': "#edc240"},
                    {'id': "dAp86%low", 'data': appredict_data["dAp86%low"], 'lines': {'show': True, 'lineWidth': 0, 'fill': False }, 'color': "#edc240"},
                    {'id': "dAp68%low", 'data': appredict_data["dAp68%low"], 'lines': {'show': True, 'lineWidth': 0, 'fill': False }, 'color': "#edc240"},
                    {'id': "dAp38%low", 'data': appredict_data["dAp38%low"], 'lines': {'show': True, 'lineWidth': 0, 'fill': False }, 'color': "#edc240"},
                    {'id': "dAp38%upp", 'data': appredict_data["dAp38%upp"], 'lines': {'show': True, 'lineWidth': 0, 'fill': 0.4 }, 'color': "#edc240", 'fillBetween': "dAp38%low"},
                    {'id': "dAp68%upp", 'data': appredict_data["dAp68%upp"], 'lines': {'show': True, 'lineWidth': 0, 'fill': 0.3 }, 'color': "#edc240", 'fillBetween': "dAp68%low"},
                    {'label': 'test label', 'id': "dAp86%upp", 'data': appredict_data["dAp86%upp"], 'lines': {'show': True, 'lineWidth': 0, 'fill': 0.2 }, 'color': "#edc240", 'fillBetween': "dAp86%low"},
                    {'label': 'test label', 'id': "dAp95%upp", 'data': appredict_data["dAp95%upp"], 'lines': {'show': True, 'lineWidth': 0, 'fill': 0.1 }, 'color': "#edc240", 'fillBetween': "dAp95%low"}];
        data['adp90'] = dataset2
#        if len(sim.voltage_results) > 1:
#            for i, percentile in enumerate(sim.voltage_results[0]['da90']):
#                if percentile == 'median_delta_APD90' or len(sim.voltage_results[0]['da90']) == 1:
#                    data['adp90'].append({'label': f'Simulation @ {sim.pacing_frequency} Hz', 'data': [], 'lines': {'show': True, 'lineWidth': 2}, 'points': {'show': True}, 'color': 0})
#                    upper_fill_offset = 0.2
#        # add adp90 and qnet data
#        for v_res, qnet in zip_longest(sim.voltage_results[1:], sim.q_net):
#            for i, da90 in enumerate(v_res['da90']):
#                data['adp90'][i]['data'].append([v_res['c'], da90])

#            da90 = v_res['da90'][median_index]
#            data['adp90'][0]['data'].append([v_res['c'], da90])
#            if qnet:
#                data['qnet'][0]['data'].append([v_res['c'], to_float(qnet['qnet'])])
#
#        # add voltage traces data
#        for i, trace in enumerate(sim.voltage_traces):
#            data['traces'].append({'color': i, 'enabled': True,
#                                   'label': f"Simulation @ {sim.pacing_frequency} Hz @ {trace['name']} µM",
#                                   'data': [[series['name'], series['value']] for series in trace['series']]})

        return JsonResponse(data=data,
                            status=200, safe=False)
