import os
import json
import shutil
import asyncio
import datetime

import httpx
import pytest
import pytest_asyncio
from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from django.utils import timezone
from files.models import IonCurrent
from simulations.models import Simulation
from simulations.views import (
    AP_MANAGER_URL,
    COMPILING_CELLML,
    INITIALISING,
    get_from_api,
    listify,
    save_api_error_sync,
    start_simulation,
    to_float,
    to_int,
)


@pytest.mark.django_db
def test_to_int():
    assert to_int(12.4) == 12.4
    assert to_int(5.0) == 5
    assert str(to_int(5.0)) == '5'


@pytest.mark.django_db
def test_to_float():
    assert to_float(12) == to_float(12.0) == to_float('12.0') == 12.0
    assert to_float('bla') == 'bla'


@pytest.mark.django_db
def test_listify():
    assert listify('bla') == ['bla']
    assert listify(['1', '2', '3']) == ['1', '2', '3']


@pytest.mark.django_db
def test_save_api_error_sync(simulation_range):
    assert simulation_range.status == Simulation.Status.NOT_STARTED 
    message = 'something went wrong' * 15
    save_api_error_sync(simulation_range, message)
    assert simulation_range.progress == 'Failed!'
    assert simulation_range.status == Simulation.Status.FAILED
    assert simulation_range.api_errors == message[:254]


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_get_from_api_new_test_method(httpx_mock, simulation_range):
    json_data = {'success': {'test_method': 'bla'}}
    httpx_mock.add_response(json=json_data)
    async with httpx.AsyncClient(timeout=None) as client:
        response = await get_from_api(client, 'test_method', simulation_range)
        assert response == json_data
        assert simulation_range.status == Simulation.Status.NOT_STARTED


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_get_from_api_random_response(httpx_mock, simulation_range):
    json_data = {'some other': 'some other response'}
    httpx_mock.add_response(json=json_data)
    async with httpx.AsyncClient(timeout=None) as client:
        response = await get_from_api(client, 'messages', simulation_range)
        assert response == json_data
        assert simulation_range.status == Simulation.Status.NOT_STARTED


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_get_from_api_returns_error_msg(httpx_mock):
    sim = await sync_to_async(Simulation)()
    json_data = {'error': 'some error message'}
    httpx_mock.add_response(json=json_data)
    async with httpx.AsyncClient(timeout=None) as client:
        response = await get_from_api(client, 'messages', sim)
        assert response == json_data
        assert sim.status == Simulation.Status.FAILED
        assert str(sim.api_errors) == 'API error message: some error message'


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_get_from_api_invalid_json_for_existing_method(httpx_mock):
    sim = await sync_to_async(Simulation)()
    json_data = {'success': 'some other response'}
    httpx_mock.add_response(json=json_data)
    async with httpx.AsyncClient(timeout=None) as client:
        response = await get_from_api(client, 'messages', sim)
        assert response == json_data
        assert sim.status == Simulation.Status.FAILED
        assert str(sim.api_errors) == "Result to call messages failed JSON validation: 'some other response' is not of type 'array'"


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_get_from_api_invalid_json_decode_error(httpx_mock):
    sim = await sync_to_async(Simulation)()
    httpx_mock.add_response(text="This is my UTF-8 content")
    async with httpx.AsyncClient(timeout=None) as client:
        response = await get_from_api(client, 'messages', sim)
        assert response == {}
        assert sim.status == Simulation.Status.FAILED
        assert str(sim.api_errors) == 'API call: messages returned invalid JSON.'


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_get_from_api_connection_error(httpx_mock):
    sim = await sync_to_async(Simulation)()
    httpx_mock.add_exception(httpx.ConnectError('Connection error'))
    async with httpx.AsyncClient(timeout=None) as client:
        response = await get_from_api(client, 'messages', sim)
        assert response == {}
        assert sim.status == Simulation.Status.FAILED
        assert str(sim.api_errors) == 'API connection failed for call: messages: Connection error.'


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_get_from_api_invalid_url(httpx_mock):
    call = 'messages'
    sim = await sync_to_async(Simulation)()
    httpx_mock.add_exception(httpx.InvalidURL('Invalid url'))
    async with httpx.AsyncClient(timeout=None) as client:
        response = await get_from_api(client, call, sim)
        assert response == {}
        assert sim.status == Simulation.Status.FAILED
        assert str(sim.api_errors) == f'Inavlid URL {AP_MANAGER_URL % (sim.ap_predict_call_id, call)}.'

@pytest.mark.django_db
def test_re_start_simulation(httpx_mock, simulation_range):
    time_in_past = datetime.datetime(1900, 1, 1)
    simulation_range.status = Simulation.Status.SUCCESS
    simulation_range.progress = '100% Completed'
    simulation_range.ap_predict_last_update = datetime.datetime(2020, 12, 25, 17, 5, 55)
    simulation_range.ap_predict_call_id = '1234567a-9ecc-11ec-b909-0242ac120002'
    simulation_range.api_errors = 'No errors'
    simulation_range.messages = ['no messages']
    simulation_range.q_net = '{}'
    simulation_range.voltage_traces = '{}'
    simulation_range.voltage_results = '{}'
    simulation_range.pkpd_results = '{}'
    simulation_range.save()
    simulation_range.refresh_from_db()

    def check_request(request: httpx.Request):
        # check call data and return mock response
        call_data = json.loads(request.content)
        assert call_data ==  {'pacingFrequency': 0.05,
                              'pacingMaxTime': 5.0,
                              'plasmaMinimum': 0.0,
                              'plasmaMaximum': 100.0,
                              'plasmaIntermediatePointCount': '4',
                              'plasmaIntermediatePointLogScale': True,
                              'modelId': '6',
                              'IKr': {'associatedData': [{'pIC50': 4.37, 'hill': 1.0, 'saturation': 0.0}]},
                              'INa': {'associatedData': [{'pIC50': 44.716, 'hill': 1.0, 'saturation': 0.0}], 'spreads': {'c50Spread': 0.2}},
                              'ICaL': {'associatedData': [{'pIC50': 70.0, 'hill': 1.0, 'saturation': 0.0}], 'spreads': {'c50Spread': 0.15}},
                              'IKs': {'associatedData': [{'pIC50': 45.3, 'hill': 1.0, 'saturation': 0.0}], 'spreads': {'c50Spread': 0.17}},
                              'IK1': {'associatedData': [{'pIC50': 41.8, 'hill': 1.0, 'saturation': 0.0}], 'spreads': {'c50Spread': 0.18}},
                              'Ito': {'associatedData': [{'pIC50': 13.4, 'hill': 1.0, 'saturation': 0.0}], 'spreads': {'c50Spread': 0.15}},
                              'INaL': {'associatedData': [{'pIC50': 52.1, 'hill': 1.0, 'saturation': 0.0}], 'spreads': {'c50Spread': 0.2}}}
        return httpx.Response(status_code=200, json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120002'}})

    httpx_mock.add_callback(check_request)
    start_simulation(simulation_range)
    assert simulation_range.status == Simulation.Status.INITIALISING
    assert simulation_range.ap_predict_call_id == '828b142a-9ecc-11ec-b909-0242ac120002'
    assert simulation_range.progress == INITIALISING
    assert time_in_past < simulation_range.ap_predict_last_update < timezone.now()
    assert simulation_range.api_errors == ''
    assert simulation_range.messages == ''
    assert simulation_range.q_net == ''
    assert simulation_range.voltage_traces == ''
    assert simulation_range.voltage_results == ''
    assert simulation_range.pkpd_results == ''

@pytest.mark.django_db
def test_start_simulation_with_ion_currents(httpx_mock, simulation_points):
    assert simulation_points.status == Simulation.Status.NOT_STARTED
    assert simulation_points.ap_predict_call_id == ''
    def check_request(request: httpx.Request):
        # check call data and return mock response
        call_data = json.loads(request.content)
        assert call_data == {'pacingFrequency': 0.05,
                             'pacingMaxTime': 5,
                             'plasmaPoints': [24.9197,
                                              25.85,
                                              27.73,
                                              35.8,
                                              41.032,
                                              42.949,
                                              56.2,
                                              62.0,
                                              67.31,
                                              72.27],
                             'modelId': '6'}
        return httpx.Response(status_code=200, json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120002'}})

    httpx_mock.add_callback(check_request)
    start_simulation(simulation_points)
    assert simulation_points.ap_predict_call_id == '828b142a-9ecc-11ec-b909-0242ac120002'
    assert simulation_points.status == Simulation.Status.INITIALISING


@pytest.mark.django_db
def test_start_simulation_pharmacokinetics(httpx_mock, simulation_pkdata):
#check call json
    assert simulation_pkdata.status == Simulation.Status.NOT_STARTED
    assert simulation_pkdata.ap_predict_call_id == ''
    # the pk data file doesn't exist
    with pytest.raises(FileNotFoundError):
        start_simulation(simulation_pkdata)

    # copy pk file
    pkd_test_source_file = os.path.join(settings.BASE_DIR, 'simulations', 'tests', 'small_sample.tsv')
    pkd_test_dest_file = os.path.join(settings.MEDIA_ROOT, str(simulation_pkdata.PK_data))
    shutil.copy(pkd_test_source_file, pkd_test_dest_file)
    assert os.path.isfile(pkd_test_dest_file)

    # test start simulation call
    httpx_mock.add_response(json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120002'}})
    start_simulation(simulation_pkdata)
    assert simulation_pkdata.ap_predict_call_id == '828b142a-9ecc-11ec-b909-0242ac120002'
    assert simulation_pkdata.status == Simulation.Status.INITIALISING

    # cleanup file (via signal)
    simulation_pkdata.delete()
    assert not os.path.isfile(pkd_test_dest_file)


@pytest.mark.django_db
def test_start_simulation_cellml_file(httpx_mock, simulation_range):
#    httpx_mock.add_response(json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120002'}})
    pass
    # test cellml_file

#def start_simulation(sim):
#    """
#    Makes the request to start the simulation.
#    """
#    # (re)set status and result
#    sim.status = Simulation.Status.NOT_STARTED
#    sim.progress = INITIALISING if sim.model.ap_predict_model_call else COMPILING_CELLML
#    sim.ap_predict_last_update = timezone.now()
#    sim.ap_predict_call_id = ''
#    sim.api_errors = ''
#    sim.messages = ''
#    sim.q_net = ''
#    sim.voltage_traces = ''
#    sim.voltage_results = ''
#    sim.pkpd_results = ''
#
#    # build json data for api call
#    call_data = {'pacingFrequency': sim.pacing_frequency,
#                 'pacingMaxTime': sim.maximum_pacing_time}
#    if sim.pk_or_concs == Simulation.PkOptions.pharmacokinetics:  # pk data file
#        with open(sim.PK_data.path, 'rb') as PK_data_file:
#            call_data['PK_data_file'] = PK_data_file.read().decode('unicode-escape')
#    elif sim.pk_or_concs == Simulation.PkOptions.compound_concentration_points:
#        call_data['plasmaPoints'] = sorted(set([c.concentration
#                                                for c in CompoundConcentrationPoint.objects.filter(simulation=sim)]))
#    else:  # sim.pk_or_concs == Simulation.PkOptions.compound_concentration_range:
#        call_data['plasmaMinimum'] = sim.minimum_concentration
#        call_data['plasmaMaximum'] = sim.maximum_concentration
#        call_data['plasmaIntermediatePointCount'] = sim.intermediate_point_count
#        call_data['plasmaIntermediatePointLogScale'] = sim.intermediate_point_log_scale
#
#    if sim.model.ap_predict_model_call:
#        call_data['modelId'] = sim.model.ap_predict_model_call
#    else:
#        with open(sim.model.cellml_file.path, 'rb') as cellml_file:
#            call_data['cellml_file'] = cellml_file.read().decode('unicode-escape')
#
#    for current_param in SimulationIonCurrentParam.objects.filter(simulation=sim):
#        call_data[current_param.ion_current.name] = {
#            'associatedData': [{'pIC50': Simulation.conversion(sim.ion_units)(current_param.current),
#                                'hill': current_param.hill_coefficient,
#                                'saturation': current_param.saturation_level}]
#        }
#        if current_param.spread_of_uncertainty:
#            call_data[current_param.ion_current.name]['spreads'] = \
#                {'c50Spread': current_param.spread_of_uncertainty}
#
#    # call api to start simulation

@pytest.mark.django_db
def test_start_simulation_json_err(httpx_mock, simulation_range):
    httpx_mock.add_response(text="This is my UTF-8 content")
    start_simulation(simulation_range)
    assert simulation_range.status == Simulation.Status.FAILED
    assert str(simulation_range.api_errors) == 'Starting simulation failed: returned invalid JSON.'


@pytest.mark.django_db
def test_start_simulation_connection_err(httpx_mock, simulation_range):
    httpx_mock.add_exception(httpx.ConnectError('Connection error'))
    start_simulation(simulation_range)
    assert simulation_range.status == Simulation.Status.FAILED
    assert str(simulation_range.api_errors) == 'API connection failed: Connection error.'


@pytest.mark.django_db
def test_start_simulation_invalid_url(httpx_mock, simulation_range):
    httpx_mock.add_exception(httpx.InvalidURL('Invalid url'))
    start_simulation(simulation_range)
    assert simulation_range.status == Simulation.Status.FAILED
    assert str(simulation_range.api_errors) == f'Inavlid URL {settings.AP_PREDICT_ENDPOINT}.'


@pytest.mark.django_db
class TestSimulationListView:
    def test_not_logged_in(self, client):
        response = client.get('/simulations/')
        assert response.status_code == 302

    def test_list(self, client, simulation_recipe, logged_in_user, other_user, o_hara_model):
        simulation_recipe.make(author=other_user, model=o_hara_model, _quantity=3)
        my_simulations = simulation_recipe.make(author=logged_in_user, model=o_hara_model, _quantity=3)

        response = client.get('/simulations/')
        assert response.status_code == 200
        assert set(response.context['object_list']) == set(my_simulations)


@pytest.mark.django_db
class TestSimulationCreateView_and_TemplateView:
    @pytest.fixture
    def new_sim_data(self, simulation_range):
        return {'ion-TOTAL_FORMS': '7',
                'ion-INITIAL_FORMS': '7',
                'concentration-TOTAL_FORMS': '5',
                'concentration-INITIAL_FORMS': '0',
                'title': 'test sim2',
                'notes': 'test notes sim2',
                'model': simulation_range.model.pk,
                'pacing_frequency': '0.05',
                'maximum_pacing_time': '5',
                'ion_current_type': 'pIC50',
                'ion_units': '-log(M)',
                'ion-0-models': '[1, 2, 3, 4, 5, 6, 7, 8]',
                'ion-0-ion_current': IonCurrent.objects.get(name='IKr').pk,
                'ion-0-current': 1,
                'ion-0-hill_coefficient': '1',
                'ion-0-saturation_level': '0',
                'ion-0-default_spread_of_uncertainty': '0.18',
                'ion-1-models': '[1, 2, 3, 4, 5, 6, 7, 8]',
                'ion-1-ion_current': IonCurrent.objects.get(name='INa').pk,
                'ion-1-current': '',
                'ion-1-default_spread_of_uncertainty': '0.2',
                'ion-2-models': '[1, 2, 3, 4, 5, 6, 7, 8]',
                'ion-2-ion_current': IonCurrent.objects.get(name='ICaL').pk,
                'ion-2-current': '0.6',
                'ion-2-hill_coefficient': '1',
                'ion-2-saturation_level': '0',
                'ion-2-default_spread_of_uncertainty': '0.15',
                'ion-3-models': '[1, 2, 3, 4, 5, 6, 7, 8]',
                'ion-3-ion_current': IonCurrent.objects.get(name='IKs').pk,
                'ion-3-current': '',
                'ion-3-default_spread_of_uncertainty': '0.17',
                'ion-4-models': '[1, 2, 3, 4, 5, 6, 7, 8]',
                'ion-4-ion_current': IonCurrent.objects.get(name='IK1').pk,
                'ion-4-current': '',
                'ion-4-default_spread_of_uncertainty': '0.18',
                'ion-5-models': '[1, 2, 3, 4, 5, 6, 7, 8]',
                'ion-5-ion_current': IonCurrent.objects.get(name='Ito').pk,
                'ion-5-current': '',
                'ion-5-default_spread_of_uncertainty': '0.15',
                'ion-6-models': '[6, 8]',
                'ion-6-ion_current': IonCurrent.objects.get(name='INaL').pk,
                'ion-6-default_spread_of_uncertainty': '0.2',
                'pk_or_concs': 'compound_concentration_range',
                'minimum_concentration': '0',
                'maximum_concentration': '100',
                'intermediate_point_count': '4',
                'intermediate_point_log_scale': 'on',
                'concentration-0-concentration': '',
                'concentration-1-concentration': '',
                'concentration-2-concentration': '',
                'concentration-3-concentration': '',
                'concentration-4-concentration': ''}

    def test_create_page_not_logged_in(self, user, client):
        response = client.get('/simulations/new')
        assert response.status_code == 302

    def test_template_page_not_logged_in(self, user, client, simulation_range):
        response = client.get('/simulations/%s/template' % simulation_range.pk)
        assert response.status_code == 302

    def test_can_create(self, logged_in_user, client, new_sim_data, httpx_mock):
        assert IonCurrent.objects.count() == 7
        assert Simulation.objects.count() == 1
        httpx_mock.add_response(json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120002'}})
        response = client.post('/simulations/new', new_sim_data)
        assert response.status_code == 302
        assert Simulation.objects.count() == 2

    def test_template_can_create(self, logged_in_user, client, new_sim_data, simulation_range, httpx_mock):
        assert IonCurrent.objects.count() == 7
        assert Simulation.objects.count() == 1
        httpx_mock.add_response(json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120002'}})
        response = client.post('/simulations/%s/template' % simulation_range.pk, new_sim_data)
        assert response.status_code == 302
        assert Simulation.objects.count() == 2

    def test_cannot_duplicate_title(self, logged_in_user, client, new_sim_data, simulation_range):
        assert Simulation.objects.count() == 1
        new_sim_data['title'] = simulation_range.title
        response = client.post('/simulations/new', data=new_sim_data)
        assert response.status_code == 200
        assert Simulation.objects.count() == 1
        simulation_range.refresh_from_db()
        assert simulation_range.notes != new_sim_data['notes']

    def test_template_cannot_duplicate_title(self, logged_in_user, client, new_sim_data, simulation_range):
        assert Simulation.objects.count() == 1
        new_sim_data['title'] = simulation_range.title
        response = client.post('/simulations/%s/template' % simulation_range.pk, data=new_sim_data)
        assert response.status_code == 200
        assert Simulation.objects.count() == 1
        simulation_range.refresh_from_db()
        assert simulation_range.notes != new_sim_data['notes']

    def test_initial(self, logged_in_user, client, simulation_range):
        response = client.get('/simulations/%d/template' % simulation_range.pk)
        assert response.context['form'].initial == {
            'notes': simulation_range.notes,
            'model': simulation_range.model,
            'pacing_frequency': simulation_range.pacing_frequency,
            'maximum_pacing_time': simulation_range.maximum_pacing_time,
            'ion_current_type': simulation_range.ion_current_type,
            'ion_units': simulation_range.ion_units,
            'pk_or_concs': simulation_range.pk_or_concs,
            'minimum_concentration': simulation_range.minimum_concentration,
            'maximum_concentration': simulation_range.maximum_concentration,
            'intermediate_point_count': simulation_range.intermediate_point_count,
            'intermediate_point_log_scale': simulation_range.intermediate_point_log_scale,
            'PK_data': simulation_range.PK_data
        }
        assert str([m.message for m in response.context['INFO_MESSAGES']]) == \
            "['Using existing simulation <em>%s</em> as a template.']" % simulation_range.title


@pytest.mark.django_db
class TestSimulationEditView:
    def test_not_logged_in(self, client, user, simulation_range):
        response = client.get('/simulations/%d/edit' % simulation_range.pk)
        assert response.status_code == 302

    def test_non_owner_cannot_edit(self, other_user, client, simulation_range):
        client.login(username=other_user.email, password='password')
        response = client.get('/simulations/%d/edit' % simulation_range.pk)
        assert response.status_code == 403

    def test_cannot_duplicate_title(self, logged_in_user, client, simulation_recipe, simulation_range, o_hara_model):
        assert simulation_range.author == logged_in_user
        new_simulation = simulation_recipe.make(author=logged_in_user, model=o_hara_model)
        assert new_simulation.title != simulation_range.title
        data = {'title': new_simulation.title, 'notes': 'new notes'}
        response = client.post('/simulations/%d/edit' % simulation_range.pk, data=data)
        assert response.status_code == 200
        simulation_range.refresh_from_db()
        assert new_simulation.title != simulation_range.title

    def test_owner_can_edit(self, logged_in_user, client, simulation_range):
        assert simulation_range.author == logged_in_user
        data = {'title': 'new title', 'notes': 'new notes'}
        response = client.post('/simulations/%d/edit' % simulation_range.pk, data=data)
        assert response.status_code == 302
        simulation_range.refresh_from_db()
        assert simulation_range.title == data['title']
        assert simulation_range.notes == data['notes']

    def test_initial(self, logged_in_user, client, simulation_range):
        response = client.get('/simulations/%d/edit' % simulation_range.pk)
        assert response.context['form'].initial == {'title': simulation_range.title, 'notes': simulation_range.notes}


@pytest.mark.django_db
class TestSimulationResultView:
    def test_non_loged_in_cannot_see(self, user, client, simulation_range):
        response = client.get('/simulations/%d/result' % simulation_range.pk)
        assert response.status_code == 302

    def test_non_owner_cannot_see(self, other_user, client, simulation_range):
        client.login(username=other_user.email, password='password')
        assert simulation_range.author != other_user
        response = client.get('/simulations/%d/result' % simulation_range.pk)
        assert response.status_code == 403

    def test_owner_can_see(self, logged_in_user, client, cellml_model_recipe, simulation_range):
        assert simulation_range.author == logged_in_user
        response = client.get('/simulations/%d/result' % simulation_range.pk)
        assert response.status_code == 200


@pytest.mark.django_db
class TestSimulationDeleteView:
    def test_owner_can_delete(self, logged_in_user, client, simulation_range):
        assert Simulation.objects.count() == 1
        response = client.post('/simulations/%d/delete' % simulation_range.pk)
        assert response.status_code == 302
        assert Simulation.objects.count() == 0

    def test_non_owner_cannot_delete(self, other_user, client, simulation_range):
        client.login(username=other_user.email, password='password')
        assert simulation_range.author != other_user
        assert Simulation.objects.count() == 1
        response = client.post('/simulations/%d/delete' % simulation_range.pk)
        assert response.status_code == 403

    def test_non_logged_in_owner_cannot_delete(self, user, client, simulation_range):
        assert simulation_range.author == user
        assert Simulation.objects.count() == 1
        response = client.post('/simulations/%d/delete' % simulation_range.pk)
        assert response.status_code == 403

