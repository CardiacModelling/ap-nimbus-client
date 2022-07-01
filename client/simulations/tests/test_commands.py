import os
import re

import pytest
from django.conf import settings
from django.core.management import call_command
from files.models import IonCurrent
from simulations.models import CompoundConcentrationPoint, Simulation, SimulationIonCurrentParam


@pytest.mark.django_db
class TestCommandLineSimulationCreate:
    def test_create_duplicate_name_concentration_range(self, logged_in_user, client, httpx_mock, o_hara_model):
        assert IonCurrent.objects.count() == 7
        assert Simulation.objects.count() == 0
        assert SimulationIonCurrentParam.objects.count() == 0
        assert CompoundConcentrationPoint.objects.count() == 0

        httpx_mock.add_response(json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120002'}})
        # use defaults
        call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA")
        assert Simulation.objects.count() == 1
        assert Simulation.objects.get(title='my title').pacing_frequency == 1.0
        assert SimulationIonCurrentParam.objects.count() == 0
        assert CompoundConcentrationPoint.objects.count() == 0

        httpx_mock.add_response(json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120003'}})
        # don't use defaults
        call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA",
                     '--pacing_frequency=4.2', '--concentration_type=compound_concentration_range',
                     '--minimum_concentration=0.0', '--maximum_concentration=100.0', '--intermediate_point_count=4',
                     '--intermediate_point_log_scale=True',
                     '--current_inhibitory_concentration', 'INa', '0.5', '1', '0', '0')
        assert Simulation.objects.count() == 2
        assert Simulation.objects.get(title='my title (2)').pacing_frequency == 4.2
        assert SimulationIonCurrentParam.objects.count() == 1
        assert CompoundConcentrationPoint.objects.count() == 0

    def test_concentration_points(self, logged_in_user, client, httpx_mock, o_hara_model):
        assert IonCurrent.objects.count() == 7
        assert Simulation.objects.count() == 0
        assert SimulationIonCurrentParam.objects.count() == 0
        assert CompoundConcentrationPoint.objects.count() == 0

        httpx_mock.add_response(json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120002'}})
        call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA",
                     '--pk_or_concs=compound_concentration_points', '--concentration_point=0.5')
        assert Simulation.objects.count() == 1
        assert SimulationIonCurrentParam.objects.count() == 0
        assert CompoundConcentrationPoint.objects.count() == 1

    def test_pk_data(self, logged_in_user, client, httpx_mock, o_hara_model):
        assert IonCurrent.objects.count() == 7
        assert Simulation.objects.count() == 0
        assert SimulationIonCurrentParam.objects.count() == 0
        assert CompoundConcentrationPoint.objects.count() == 0

        pkd_test_source_file = os.path.join(settings.BASE_DIR, 'simulations', 'tests', 'small_sample.tsv')
        httpx_mock.add_response(json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120002'}})
        call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA",
                     '--pk_or_concs=pharmacokinetics', f'--PK_data_file={pkd_test_source_file}',
                     '--ion_units=M', '--ion_current_type=IC50')
        assert Simulation.objects.count() == 1
        assert SimulationIonCurrentParam.objects.count() == 0
        assert str(Simulation.objects.get(title='my title').PK_data).endswith('.tsv')
        assert Simulation.objects.get(title='my title').ion_current_type == 'IC50'
        assert Simulation.objects.get(title='my title').ion_units == 'M'

    def test_ambiguous_model(self, logged_in_user, client, httpx_mock, o_hara_model, cellml_model_recipe, other_user):
        cellml_model_recipe.make(
            author=other_user,
            predefined=True,
            name="O'Hara-Rudy-CiPA",
            description='human ventricular cell model (endocardial)',
            version='v2.0',
            year=2022,
            cellml_link='',
            paper_link='',
            ap_predict_model_call='11'
        )
        assert Simulation.objects.count() == 0

        with pytest.raises(ValueError, match='Ambiguous specification of model'):
            call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA")
        assert Simulation.objects.count() == 0

        # disambiguate model
        httpx_mock.add_response(json={'success': {'id': '828b142a-9ecc-11ec-b909-0242ac120002'}})
        call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA", '--model_year=2022',
                     '--model_version=v2.0', '--ion_current_type=IC50')
        assert Simulation.objects.count() == 1
        assert Simulation.objects.first().ion_current_type == 'IC50'
        assert Simulation.objects.first().ion_units == 'µM'

    def test_wrong_unit_types(self, logged_in_user, client, httpx_mock, o_hara_model):
        with pytest.raises(ValueError, match=re.escape("pIC50's are only available with ion_units -log(M)")):
            call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA",
                         '--ion_current_type=pIC50', '--ion_units==M')

    def test_wrong_current_type(self, logged_in_user, client, httpx_mock, o_hara_model):
        with pytest.raises(ValueError, match=re.escape('Incorrect specification of ion_current_type')):
            call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA",
                         '--ion_current_type=bla')

    def test_wrong_concentration_type(self, logged_in_user, client, httpx_mock, o_hara_model):
        with pytest.raises(ValueError, match='Invalid concentration_type'):
            call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA", '--pk_or_concs=bla')

    def test_wrong_max_concentration(self, logged_in_user, client, httpx_mock, o_hara_model):
        with pytest.raises(ValueError, match='maximum_concentration needs to be larger than minimum_concentration'):
            call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA",
                         '--maximum_concentration=10', '--minimum_concentration=100')

    def test_wrong_point_count(self, logged_in_user, client, httpx_mock, o_hara_model):
        with pytest.raises(ValueError, match='Invalid intermediate_point_count'):
            call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA",
                         '--intermediate_point_count=-1')

        with pytest.raises(ValueError, match='Invalid intermediate_point_count'):
            call_command('start_simulation', 'my title', logged_in_user.email, "O'Hara-Rudy-CiPA",
                         '--intermediate_point_count=100')
