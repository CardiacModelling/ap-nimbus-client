import asyncio
import copy
import io
import sys
from itertools import zip_longest
from json.decoder import JSONDecodeError
from urllib.parse import urljoin

import httpx
import jsonschema
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

from .forms import (
    CompoundConcentrationPointFormSet,
    IonCurrentFormSet,
    SimulationEditForm,
    SimulationForm,
)
from .models import CompoundConcentrationPoint, Simulation, SimulationIonCurrentParam


DONE = '..done!'
INITIALISING = 'Initialising..'
COMPILING_CELLML = 'Converting CellML...'
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
                                  'additionalProperties': False}},


    'pkpd_results': {'type': 'array',
                     'items': {'type': 'object',
                               'properties': {'timepoint': {'type': 'string'},
                                              'apd90': {"anyOf": [{'type': 'string'},
                                                                  {'type': 'array',
                                                                   'items': {'type': 'string'}}]}},
                               'required': ['apd90', 'timepoint'],
                               'additionalProperties': False}},
    'messages': {'type': 'array',
                 'items': {'type': 'string'}},
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


def listify(val):
    """
    Return the list given or a single element list if given a string
    """
    if isinstance(val, str):
        return [val]
    return val


async def save_api_error(sim, message):
    sim.progress = 'Failed!'
    sim.status = Simulation.Status.FAILED
    sim.api_errors = message[:254]
    await sync_to_async(sim.save)()


save_api_error_sync = async_to_sync(save_api_error)


async def get_from_api(client, call, sim):
    """
    Get the result of an API call
    """
    response = {}
    try:
        res = await client.get(AP_MANAGER_URL % (sim.ap_predict_call_id, call), timeout=None)
        response = res.json()
        if 'error' in response:
            await save_api_error(sim, f"API error message: {str(response['error'])}")
    except JSONDecodeError:
        await save_api_error(sim, f'API call: {call} returned invalid JSON.')
    except httpx.HTTPError as e:
        await save_api_error(sim, f'API connection failed for call: {call}: {str(e)}.')
    except httpx.InvalidURL:
        await save_api_error(sim, f'Inavlid URL {AP_MANAGER_URL % (sim.ap_predict_call_id, call)}.')
    finally:
        try:  # validate a succesful result if we have a schema for it
            if 'success' in response and call in JSON_SCHEMAS:
                jsonschema.validate(instance=response['success'], schema=JSON_SCHEMAS[call])
        except jsonschema.exceptions.ValidationError as e:
            await save_api_error(sim, f'Result to call {call} failed JSON validation: {e.message}')
        finally:
            return response


def start_simulation(sim):
    """
    Makes the request to start the simulation.
    """
    # (re)set status and result
    sim.status = Simulation.Status.NOT_STARTED
    sim.progress = INITIALISING if sim.model.ap_predict_model_call else COMPILING_CELLML
    sim.ap_predict_last_update = timezone.now()
    sim.ap_predict_call_id = ''
    sim.api_errors = ''
    sim.messages = ''
    sim.q_net = ''
    sim.voltage_traces = ''
    sim.voltage_results = ''
    sim.pkpd_results = ''

    # build json data for api call
    call_data = {'pacingFrequency': sim.pacing_frequency,
                 'pacingMaxTime': sim.maximum_pacing_time}
    if sim.pk_or_concs == Simulation.PkOptions.pharmacokinetics:  # pk data file
        with open(sim.PK_data.path, 'rb') as PK_data_file:
            call_data['PK_data_file'] = PK_data_file.read().decode('unicode-escape')
    elif sim.pk_or_concs == Simulation.PkOptions.compound_concentration_points:
        call_data['plasmaPoints'] = sorted(set([c.concentration
                                                for c in CompoundConcentrationPoint.objects.filter(simulation=sim)]))
    else:  # sim.pk_or_concs == Simulation.PkOptions.compound_concentration_range:
        call_data['plasmaMinimum'] = sim.minimum_concentration
        call_data['plasmaMaximum'] = sim.maximum_concentration
        call_data['plasmaIntermediatePointCount'] = sim.intermediate_point_count
        call_data['plasmaIntermediatePointLogScale'] = sim.intermediate_point_log_scale

    if sim.model.ap_predict_model_call:
        call_data['modelId'] = sim.model.ap_predict_model_call
    else:
        with open(sim.model.cellml_file.path, 'rb') as cellml_file:
            call_data['cellml_file'] = cellml_file.read().decode('unicode-escape')

    for current_param in SimulationIonCurrentParam.objects.filter(simulation=sim):
        call_data[current_param.ion_current.name] = {
            'associatedData': [{'pIC50': Simulation.conversion(sim.ion_units)(current_param.current),
                                'hill': current_param.hill_coefficient,
                                'saturation': current_param.saturation_level}]
        }
        if current_param.spread_of_uncertainty:
            call_data[current_param.ion_current.name]['spreads'] = \
                {'c50Spread': current_param.spread_of_uncertainty}

    # call api to start simulation
    try:
        response = httpx.post(settings.AP_PREDICT_ENDPOINT, json=call_data).json()
        if 'error' in response:
            save_api_error_sync(sim, f"API error message: {response['error']}")
        else:
            sim.ap_predict_call_id = response['success']['id']
            sim.status = Simulation.Status.INITIALISING
            sim.save()
    except JSONDecodeError:
        save_api_error_sync(sim, 'Starting simulation failed: returned invalid JSON.')
    except httpx.HTTPError as e:
        save_api_error_sync(sim, f'API connection failed: {str(e)}.')
    except httpx.InvalidURL:
        save_api_error_sync(sim, f'Inavlid URL {settings.AP_PREDICT_ENDPOINT}.')


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
        worksheet = workbook.add_worksheet('Input Values')
        row = 0
        worksheet.write(row, 0, 'Title', bold)
        worksheet.write(row, 1, sim.title)
        row += 1

        worksheet.write(row, 0, 'Created at', bold)
        worksheet.write(row, 2, str(sim.created_at))
        row += 1

        worksheet.write(row, 0, 'Created by', bold)
        worksheet.write(row, 2, sim.author.full_name)
        row += 2

        worksheet.write(row, 0, 'Model', bold)
        worksheet.write(row, 1, str(sim.model))
        row += 2

        worksheet.write(row, 1, 'Pacing', bold)
        worksheet.write(row, 2, 'Frequency', bold)
        worksheet.write(row, 3, sim.pacing_frequency)
        worksheet.write(row, 4, 'Hz')
        row += 1

        worksheet.write(row, 2, 'Max time', bold)
        worksheet.write(row, 3, sim.maximum_pacing_time)
        worksheet.write(row, 4, 'mins')
        row += 2

        worksheet.write(row, 0, 'Ion Channel Current Inhibitory Concentrations', bold)
        worksheet.write(row, 3, 'Hill Coefficient', bold)
        worksheet.write(row, 4, 'Saturation Level (%)', bold)
        worksheet.write(row, 5, 'Spread of Uncertainty', bold)
        worksheet.write(row, 6, 'Channel protein', bold)
        worksheet.write(row, 7, 'Gene', bold)
        worksheet.write(row, 8, 'Description', bold)
        row += 1

        for current in SimulationIonCurrentParam.objects.filter(simulation=sim):
            worksheet.write(row, 0, current.ion_current.name)
            worksheet.write(row, 1, current.current)
            worksheet.write(row, 2, sim.ion_units)
            worksheet.write(row, 3, current.hill_coefficient)
            worksheet.write(row, 4, current.saturation_level)
            worksheet.write(row, 5, current.spread_of_uncertainty)
            worksheet.write(row, 6, current.ion_current.channel_protein.replace('<sub>', ''). replace('</sub>', ' '))
            worksheet.write(row, 7, current.ion_current.gene)
            worksheet.write(row, 8, current.ion_current.description)
            row += 1

        row += 1
        if sim.pk_or_concs == Simulation.PkOptions.compound_concentration_range:
            worksheet.write(row, 0, 'Compound Concentration Range', bold)
            worksheet.write(row, 1, 'Minimum Concentration', bold)
            worksheet.write(row, 2, sim.minimum_concentration)
            row += 1

            worksheet.write(row, 1, 'Maximum Concentration', bold)
            worksheet.write(row, 2, sim.maximum_concentration)
            row += 1

            worksheet.write(row, 1, 'Intermediate Point Count', bold)
            worksheet.write(row, 2, sim.intermediate_point_count)
            row += 1

            worksheet.write(row, 1, 'Intermediate Point Log Scale', bold)
            worksheet.write(row, 2, sim.intermediate_point_log_scale)
            row += 1
        elif sim.pk_or_concs == Simulation.PkOptions.compound_concentration_points:
            worksheet.write(row, 0, 'Compound Concentration Points', bold)
            for point in CompoundConcentrationPoint.objects.filter(simulation=sim):
                worksheet.write(row, 1, point.concentration)
                row += 1
        else:
            worksheet.write(row, 0, 'PK data file', bold)
            worksheet.write(row, 1, str(sim.PK_data))
            row += 1
        row += 1
        worksheet.write(row, 0, 'Notes', bold)
        worksheet.write(row, 1, sim.notes)

    def qNet(self, workbook, bold, sim):
        def len_vr():
            if not sim.voltage_results or not 'da90' in sim.voltage_results[0]:
                return 0
            return (len(sim.voltage_results[0]['da90'])) -1

        worksheet = workbook.add_worksheet('% Change and qNet')
        row = 0
        worksheet.write(row, 0, 'Concentration (µM)', bold)
        worksheet.write(row, 1, 'Δ APD90 (%)', bold)
        col = 2
        col += len_vr()
        worksheet.write(row, col, 'qNet (C/F)', bold)
        col += 1
        col += len_vr()
        worksheet.write(row, col, 'PeakVm(mV)', bold)
        worksheet.write(row, col + 1, 'UpstrokeVelocity(mV/ms)', bold)
        worksheet.write(row, col + 2, 'APD50(ms)', bold)
        worksheet.write(row, col + 3, 'APD90(ms)', bold)
        row += 1

        if not sim.voltage_results:
            return

        for da_col, da90_head in enumerate(sim.voltage_results[0]['da90']):
            worksheet.write(row, da_col + 1, da90_head, bold)
        if len(sim.voltage_results[0]['da90']) > 1:
            for qnet_col, da90_head in enumerate(sim.voltage_results[0]['da90']):
                worksheet.write(row, da_col + qnet_col + 2, da90_head, bold)
        row += 1

        for v_res, qnet in zip_longest(sim.voltage_results[1:], (sim.q_net if sim.q_net else [])):
            worksheet.write(row, 0, to_float(v_res['c']))
            for da_col, da90 in enumerate(v_res['da90']):
                worksheet.write(row, da_col + 1, to_float(da90))
            if not qnet:
                qnet_col = 0
                worksheet.write(row, da_col + 2, 'n/a')
            else:
                for qnet_col, qnet_val in enumerate(qnet['qnet'].split(',')):
                    worksheet.write(row, da_col + qnet_col + 2, to_float(qnet_val) if qnet else 'n/a')

            worksheet.write(row, da_col + qnet_col + 3, to_float(v_res['pv']))
            worksheet.write(row, da_col + qnet_col + 4, to_float(v_res['uv']))
            worksheet.write(row, da_col + qnet_col + 5, to_float(v_res['a50']))
            worksheet.write(row, da_col + qnet_col + 6, to_float(v_res['a90']))
            row += 1

    def voltage_traces(self, workbook, bold, sim):
        worksheet = workbook.add_worksheet('Voltage Traces (concentration)')
        if not sim.voltage_traces:
            return

        column = 0
        for trace in sim.voltage_traces:
            worksheet.write(0, column, 'Conc. %s µM' % trace['name'], bold)
            worksheet.write(1, column, 'Time (ms)', bold)
            worksheet.write(1, column + 1, 'Membrane Voltage (mV)', bold)
            for i, series in enumerate(trace['series']):
                row = i + 2
                worksheet.write(row, column, to_float(series['name']))
                worksheet.write(row, column + 1, to_float(series['value']))
            column += 3

    def pkpd_results(self, workbook, bold, sim):
        worksheet = workbook.add_worksheet('PKPD - APD90 vs. Timepoint')
        worksheet.write(0, 0, 'Timepoint (h)', bold)
        worksheet.write(0, 1, 'APD90 (ms)', bold)
        if not sim.pkpd_results:
            return
        for row, pkpd in enumerate(sim.pkpd_results):
            worksheet.write(row + 1, 0, to_float(pkpd['timepoint']))
            apd90_lst = listify(pkpd['apd90'])
            for column, adp90 in enumerate(apd90_lst):
                worksheet.write(row + 1, column + 1, to_float(adp90))

    def voltage_traces_plot(self, workbook, bold, sim):
        # gather and sort all the different timepoints used in any of the series
        # not all series uses every timepoint, so we need to know which ones exist in order for printing
        worksheet = workbook.add_worksheet('Voltage Traces (Plot format)')
        worksheet.write(0, 0, 'Time (ms)', bold)
        if not sim.voltage_traces:
            return


        time_keys = set()
        for trace in sim.voltage_traces:
            for series in trace['series']:
                time_keys.add(to_float(series['name']))
        time_keys = sorted(time_keys)

        column = 1
        for trace in sim.voltage_traces:
            worksheet.write(0, column, 'Conc. %s µM' % trace['name'], bold)
            column += 1

        for i, time in enumerate(time_keys):
            worksheet.write(i + 1, 0, time)

        for i, trace in enumerate(sim.voltage_traces):
            column = i + 1
            for series in trace['series']:
                row = time_keys.index(to_float(series['name'])) + 1
                worksheet.write(row, column, to_float(series['value']))

    def get(self, request, *args, **kwargs):
        sim = self.get_object()
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        bold = workbook.add_format({'bold': True})
        self.input_values(workbook, bold, sim)
        self.qNet(workbook, bold, sim)
        self.pkpd_results(workbook, bold, sim)
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

    COMMANDS = ('q_net', 'voltage_traces', 'voltage_results', 'pkpd_results', 'messages')

    @classonlymethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view._is_coroutine = asyncio.coroutines._is_coroutine
        return view

    async def save_data(self, client, command, sim):
        response = await get_from_api(client, command, sim)
        if response and 'success' in response:
            setattr(sim, command, response['success'])

    async def update_sim(self, client, sim):
        response = await get_from_api(client, 'progress_status', sim)
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
            await save_api_error(sim, ('Progress timeout. Progress not changed for more than '
                                       f'{settings.AP_PREDICT_STATUS_TIMEOUT} seconds.'))
        elif not progress_changed or progress_text == DONE:
            # If there is no change, or if we are done see if we have stopped and try to save data
            # check if the simulation has stopped
            stop_response = await get_from_api(client, 'STOP', sim)
            if stop_response and 'success' in stop_response and stop_response['success']:
                # simulation has stopped, try to save results
                await asyncio.wait([asyncio.ensure_future(self.save_data(client, command, sim))
                                    for command in self.COMMANDS])

                if sim.status != Simulation.Status.FAILED:  # if we didn't fail saving
                    # check we have voltage_traces
                    if sim.voltage_traces and sim.status != Simulation.Status.FAILED:
                        sim.status = Simulation.Status.SUCCESS
                        sim.progress = 'Completed'
                        sim.api_errors = ''
                    else:  # we didn't get any data after stopping, we must have stopped prematurely
                        await save_api_error(sim, ('Simulation stopped prematurely. '
                                                   '(No data available after simulation stopped).'))
        await sync_to_async(sim.save)()

    async def get(self, request, *args, **kwargs):
        authenticated, user_pk = await sync_to_async(lambda req: (req.user.is_authenticated, req.user.pk))(request)
        if not authenticated:  # user login is required
            return HttpResponseNotFound()

        pks = set(map(int, self.kwargs['pks'].strip('/').split('/')))
        # get simulations to get status for and the ones that need updating
        simulations = Simulation.objects.filter(author__pk=user_pk, pk__in=pks)
        if self.kwargs['update'].lower() == 'false':
            sims_to_update = await sync_to_async(list)(simulations.exclude(status=Simulation.Status.SUCCESS))
            if sims_to_update:
                async with httpx.AsyncClient(timeout=None) as client:
                    await asyncio.wait([asyncio.ensure_future(self.update_sim(client, sim)) for sim in sims_to_update])

        # gather data for status responses
        data = await sync_to_async(lambda sims: [{'pk': sim.pk,
                                                  'progress': sim.progress,
                                                  'status': sim.status} for sim in sims])(simulations)
        return JsonResponse(data=data,
                            status=200, safe=False)


class DataSimulationView(LoginRequiredMixin, UserPassesTestMixin, UserFormKwargsMixin, DetailView):

    """
    Retrieves the data (in json format) for rendering the graphs.
    """
    model = Simulation

    def test_func(self):
        return self.get_object().author == self.request.user

    def get(self, request, *args, **kwargs):
        def update_unassigned(unasgn, val):
            """
            Updates whether we have seen unassigned qnet values.
            If so we'll have to set a manual scale for the graph.
            """

            if val <= -1.0e+200:
                unasgn['unassigned'], unasgn['min_scale'] = True, 2.0
            elif val >= 1.0e+200:
                unasgn['unassigned'], unasgn['max_scale'] = True, 2.0
            else:
                unasgn['max'], unasgn['min'] = max(unasgn['max'], val), min(unasgn['min'], val)
        adp90_unasgn = {'unassigned': False, 'max': sys.float_info.min, 'min': sys.float_info.max,
                        'min_scale': 1.1, 'max_scale': 1.1}
        qnet_unasgn = {'unassigned': False, 'max': sys.float_info.min, 'min': sys.float_info.max,
                       'min_scale': 1.1, 'max_scale': 1.1}
        pkpd_unasgn = {'unassigned': False, 'max': sys.float_info.min, 'min': sys.float_info.max,
                       'min_scale': 1.1, 'max_scale': 1.1}

        sim = self.get_object()
        data = {'adp90': [],
                'qnet': [],
                'traces': [],
                'pkpd_results': [],
                'messages': sim.messages}

        # headers
        num_percentiles = 0  # count number of percentiles, we assume we'll see the low ones first
        fill_alpha = 0.3
        requested_concentrations = None
        if sim.pk_or_concs == Simulation.PkOptions.compound_concentration_points:
            requested_concentrations = tuple(to_float(c.concentration)
                                             for c in CompoundConcentrationPoint.objects.filter(simulation=sim))

        if len(sim.voltage_results) > 1:
            for percentile in sim.voltage_results[0]['da90']:
                pct_label = f'Simulation @ {sim.pacing_frequency}Hz'
                linewidth = 2
                if '%' in percentile:
                    pct_label += percentile.replace('%upp', '% upper').replace('%low', '% lower').replace('dAp', ' ')\
                        .replace('delta_APD90(%)', '')
                    linewidth = 0 if len(sim.voltage_results[0]['da90']) > 1 else 2
                series_dict = {'enabled': True, 'label': pct_label, 'id': percentile, 'data': [], 'color': "#edc240",
                               'lines': {'show': True, 'lineWidth': linewidth, 'fill': False},
                               'points': {'show': percentile == 'median_delta_APD90'
                                          or len(sim.voltage_results[0]['da90']) == 1}}
                if 'upp' in percentile:
                    series_dict['lines']['fill'] = fill_alpha
                    series_dict['fillBetween'] = percentile.replace('upp', 'low')
                    fill_alpha -= 0.3 / (num_percentiles)
                else:
                    num_percentiles += 1
                data['adp90'].append(series_dict)
                if sim.q_net:
                    data['qnet'].append(copy.deepcopy(series_dict))

            for v_res, qnet in zip_longest(sim.voltage_results[1:], sim.q_net):
                # cut off data for concentrations we haven't asked fro from qnet/adp90 graphs
                if requested_concentrations and to_float(v_res['c']) not in requested_concentrations:
                    continue
                for i, da90 in enumerate(v_res['da90']):
                    val = to_float(da90)
                    data['adp90'][i]['data'].append([v_res['c'], val])
                    update_unassigned(adp90_unasgn, val)
                if qnet:
                    for i, qnet in enumerate(qnet['qnet'].split(',')):
                        val = to_float(qnet)
                        data['qnet'][i]['data'].append([v_res['c'], val])
                        update_unassigned(qnet_unasgn, val)

        # add pkd_results data
        if len(sim.pkpd_results) > 1:
            for i, _ in enumerate(listify(sim.pkpd_results[0]['apd90'])):
                data['pkpd_results'].append({'label': f'Concentration {i + 1}', 'id': i, 'data': [],
                                             'lines': {'show': True, 'lineWidth': 2, 'fill': False},
                                             'points': {'show': False}, 'enabled': True})
            for res in listify(sim.pkpd_results):
                for i, conc in enumerate(listify(res['apd90'])):
                    val = to_float(conc)
                    data['pkpd_results'][i]['data'].append([res['timepoint'], val])
                    update_unassigned(pkpd_unasgn, val)

        # scale y axis if there are unassigned values for qnet / adp90
        if adp90_unasgn['unassigned']:
            data['adp90_y_scale'] = {'min': adp90_unasgn['min_scale'] * adp90_unasgn['min'],
                                     'max': adp90_unasgn['max_scale'] * adp90_unasgn['max'], 'autoScale': 'none'}
        if qnet_unasgn['unassigned']:
            data['qnet_y_scale'] = {'min': qnet_unasgn['min_scale'] * qnet_unasgn['min'],
                                    'max': qnet_unasgn['max_scale'] * qnet_unasgn['max'], 'autoScale': 'none'}
        if pkpd_unasgn['unassigned']:
            data['pkpd_results_y_scale'] = {'min': pkpd_unasgn['min_scale'] * pkpd_unasgn['min'],
                                            'max': pkpd_unasgn['max_scale'] * pkpd_unasgn['max'], 'autoScale': 'none'}

        # add voltage traces data
        for i, trace in enumerate(sim.voltage_traces):
            data['traces'].append({'color': i, 'enabled': True,
                                   'label': f"Simulation @ {sim.pacing_frequency} Hz @ {trace['name']} µM",
                                   'data': [[series['name'], series['value']] for series in trace['series']]})

        return JsonResponse(data=data,
                            status=200, safe=False)

