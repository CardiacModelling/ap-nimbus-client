import os

import pytest
from django.conf import settings
from django.core.management import call_command
from files.models import IonCurrent
from simulations.models import CompoundConcentrationPoint, Simulation, SimulationIonCurrentParam


@pytest.mark.django_db
class TestCommandLineSimulationCreate:
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

    def test_create_duplicate_name_concentration_range(self, logged_in_user, client, new_sim_data, httpx_mock):
        assert IonCurrent.objects.count() == 7
        assert Simulation.objects.count() == 1
        assert SimulationIonCurrentParam.objects.count() == 7
        assert CompoundConcentrationPoint.objects.count() == 0

        httpx_mock.add_response(json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120002'}})
        # use defaults
        call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA")
        assert Simulation.objects.count() == 2
        assert Simulation.objects.get(title='my title').pacing_frequency == 1.0
        assert SimulationIonCurrentParam.objects.count() == 7
        assert CompoundConcentrationPoint.objects.count() == 0

        httpx_mock.add_response(json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120003'}})
        # don't use defaults
        call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA",
                     '--pacing_frequency=4.2', '--concentration_type=compound_concentration_range',
                     '--minimum_concentration=0.0', '--maximum_concentration=100.0', '--intermediate_point_count=4',
                     '--intermediate_point_log_scale=True',
                     '--current_inhibitory_concentration', 'INa', '0.5', '1', '0', '0')
        assert Simulation.objects.count() == 3
        assert Simulation.objects.get(title='my title (2)').pacing_frequency == 4.2
        assert SimulationIonCurrentParam.objects.count() == 8
        assert CompoundConcentrationPoint.objects.count() == 0

    def test_concentration_points(self, logged_in_user, client, new_sim_data, httpx_mock):
        assert IonCurrent.objects.count() == 7
        assert Simulation.objects.count() == 1
        assert SimulationIonCurrentParam.objects.count() == 7
        assert CompoundConcentrationPoint.objects.count() == 0

        httpx_mock.add_response(json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120002'}})
        call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA",
                     '--pk_or_concs=compound_concentration_points', '--concentration_point=0.5')
        assert Simulation.objects.count() == 2
        assert SimulationIonCurrentParam.objects.count() == 7
        assert CompoundConcentrationPoint.objects.count() == 1

    def test_pk_data(self, logged_in_user, client, new_sim_data, httpx_mock):
        assert IonCurrent.objects.count() == 7
        assert Simulation.objects.count() == 1
        assert SimulationIonCurrentParam.objects.count() == 7
        assert CompoundConcentrationPoint.objects.count() == 0

        pkd_test_source_file = os.path.join(settings.BASE_DIR, 'simulations', 'tests', 'small_sample.tsv')
        httpx_mock.add_response(json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120002'}})
        call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA",
                     '--pk_or_concs=pharmacokinetics', f'--PK_data_file={pkd_test_source_file}')
        assert Simulation.objects.count() == 2
        assert SimulationIonCurrentParam.objects.count() == 7
        assert str(Simulation.objects.get(title='my title').PK_data).endswith('.tsv')
