import os
import uuid
from shutil import copyfile

import pytest
from django.conf import settings
from django.core.files.uploadedfile import TemporaryUploadedFile
from files.models import IonCurrent
from simulations.forms import (
    CompoundConcentrationPointForm,
    CompoundConcentrationPointFormSet,
    IonCurrentForm,
    SimulationEditForm,
    SimulationForm,
)
from simulations.models import CompoundConcentrationPoint, Simulation


@pytest.mark.django_db
class TestCompoundConcentrationPointFormSet:
    @pytest.fixture
    def simulation(self, user, simulation_recipe, o_hara_model):
        return simulation_recipe.make(model=o_hara_model,
                                      pk_or_concs=Simulation.PkOptions.compound_concentration_points)

    @pytest.fixture
    def values(self):
        return [2.23, 20.25, 42.43, 66.71, 90.23, 85.24, 55.53, None]

    @pytest.fixture
    def sorted_values(self, values):
        return sorted(filter(None, values))

    @pytest.mark.django_db
    def test_CompoundConcentrationPointFormSet(self, user, simulation, values, sorted_values):
        assert CompoundConcentrationPoint.objects.count() == 0
        data = {'concentration-' + str(i) + '-concentration': c for i, c in enumerate(values)}
        data['concentration-TOTAL_FORMS'] = len(values)
        data['concentration-INITIAL_FORMS'] = 5
        formset = CompoundConcentrationPointFormSet(data, prefix='concentration', form_kwargs={'user': user})
        assert formset.is_valid()
        saved_points = formset.save(simulation)
        assert CompoundConcentrationPoint.objects.count() == len(sorted_values), str(saved_points) + '\n\n\n'
        assert [c.concentration for c in CompoundConcentrationPoint.objects.all()] == sorted_values

    @pytest.mark.django_db
    def test_CompoundConcentrationPointForm(self, user, simulation, values, sorted_values):
        assert CompoundConcentrationPoint.objects.count() == 0
        for val in values:
            form = CompoundConcentrationPointForm(user=user, data={'concentration': val})
            assert form.is_valid()
            form.save(simulation)
        assert CompoundConcentrationPoint.objects.count() == len(sorted_values)
        assert [c.concentration for c in CompoundConcentrationPoint.objects.all()] == sorted_values


@pytest.mark.django_db
class TestSimulationForm_and_SimulationEditForm:
    def upload_file(self, tmp_path, file_name):
        test_file = os.path.join(settings.BASE_DIR, 'simulations', 'tests', file_name)
        tsv_file = str(uuid.uuid4()) + file_name + '.temp'
        temp_file = os.path.join(tmp_path, tsv_file)
        assert os.path.isfile(test_file), str(test_file)
        copyfile(test_file, temp_file)
        assert os.path.isfile(temp_file)

        tempfile = TemporaryUploadedFile(tsv_file, 'text/plain', os.path.getsize(test_file), 'utf-8')
        tempfile.file = open(temp_file, 'rb')
        return tempfile

    @pytest.fixture
    def range_data(self, user, o_hara_model):
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
    def test_PK_data(self, range_data, user, tmp_path):
        assert Simulation.objects.count() == 0
        sample = self.upload_file(tmp_path, 'sample.tsv')

        # test uploading works
        form = SimulationForm(range_data, {'PK_data': sample}, user=user)
        assert form.is_valid()
        sim = form.save()
        assert Simulation.objects.count() == 1
        assert os.path.isfile(os.path.join(settings.MEDIA_ROOT, str(sample)))

        # test deleting model deletes file
        sim.delete()
        assert Simulation.objects.count() == 0
        assert not os.path.isfile(os.path.join(settings.MEDIA_ROOT, str(sample)))

    @pytest.mark.django_db
    def test_PK_data_validator(self, range_data, user, tmp_path):
        assert Simulation.objects.count() == 0
        sample = self.upload_file(tmp_path, 'error-mimetype.tsv')
        form = SimulationForm(range_data, {'PK_data': sample}, user=user)
        assert not form.is_valid()

        sample = self.upload_file(tmp_path, 'error-num-cols.tsv')
        form = SimulationForm(range_data, {'PK_data': sample}, user=user)
        assert not form.is_valid()

        sample = self.upload_file(tmp_path, 'error-not-number.tsv')
        form = SimulationForm(range_data, {'PK_data': sample}, user=user)
        assert not form.is_valid()

        sample = self.upload_file(tmp_path, 'error-negative.tsv')
        form = SimulationForm(range_data, {'PK_data': sample}, user=user)
        assert not form.is_valid()

        sample = self.upload_file(tmp_path, 'error-time.tsv')
        form = SimulationForm(range_data, {'PK_data': sample}, user=user)
        assert not form.is_valid()

        assert Simulation.objects.count() == 0

    @pytest.mark.django_db
    def test_StrictlyGreaterValidator(self, range_data, user):
        # test simulations.models.StrictlyGreaterValidator
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
        assert simulation_range.title == 'range model'
        assert simulation_range.notes == 'new notes'

        # try to chnage title to that of another model
        range_data['title'] = simulation_points.title
        form = SimulationEditForm(user=user, data=range_data, instance=simulation_range)
        assert not form.is_valid()
        assert simulation_range.title == 'range model'
        assert simulation_range.notes == 'new notes'

