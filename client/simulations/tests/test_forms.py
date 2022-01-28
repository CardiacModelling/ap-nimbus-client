import pytest

from simulations.forms import IonCurrentForm, CompoundConcentrationPointForm, SimulationForm, SimulationEditForm
from simulations.models import Simulation



@pytest.mark.django_db
class TestSimulationForm:
    @pytest.fixture
    def range_data(user, o_hara_model):
        return {'title': 'range model',
                'notes': 'some notes',
                'model': o_hara_model.pk,
                'pacing_frequency': 0.05,
                'maximum_pacing_time': 5,
                'ion_current_type': Simulation.IonCurrentType.PIC50,
                'ion_units': Simulation.IonCurrentUnits.negLogM,
                'pk_or_concs': Simulation.PkOptions.compound_concentration_range,
                'minimum_concentration': 0,
                'maximum_concentration': 100,
                'intermediate_point_count': '4',
                'intermediate_point_log_scale': True}

    @pytest.mark.django_db
    def test_SimulationForm(self, range_data, user):
        assert Simulation.objects.count() == 0
        form = SimulationForm(user=user, data=range_data)
        assert form.is_valid()
        form.save()
        assert Simulation.objects.count() == 1
        # duplicate title
        form = SimulationForm(user=user, data=range_data)
        assert not form.is_valid()

    @pytest.mark.django_db
    def test_SimulationForm_maximum_pacing_time(self, range_data, user):
        range_data['maximum_pacing_time'] = 0
        assert Simulation.objects.count() == 0
        form = SimulationForm(user=user, data=range_data)
        assert not form.is_valid()


    @pytest.mark.django_db
    def test_SimulationEditForm(self, range_data, user, simulation_range, simulation_points):
        assert Simulation.objects.count() == 2
        assert simulation_range.title == 'my simulation1'
        assert simulation_range.notes == 'some notes'

        # change title
        form = SimulationEditForm(user=user, data=range_data, instance=simulation_range)
        assert form.is_valid()
        form.save()
        assert Simulation.objects.count() == 2
        assert simulation_range.title == 'range model'
        assert simulation_range.notes == 'some notes'

        # change notes but not tile
        range_data['notes'] = 'new notes'
        form = SimulationEditForm(user=user, data=range_data, instance=simulation_range)
        assert form.is_valid()
        form.save()
        assert Simulation.objects.count() == 2
        assert simulation_range.title ==  'range model'
        assert simulation_range.notes == 'new notes'

        # try to chnage title to that of another model
        range_data['title'] = simulation_points.title
        form = SimulationEditForm(user=user, data=range_data, instance=simulation_range)
        assert not form.is_valid()
        assert simulation_range.title ==  'range model'
        assert simulation_range.notes == 'new notes'

