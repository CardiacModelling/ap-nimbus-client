import os
import uuid
from shutil import copyfile

import pytest
from django.conf import settings
from django.core.files.uploadedfile import TemporaryUploadedFile
from files.forms import CellmlModelForm
from files.models import CellmlModel, IonCurrent


@pytest.mark.django_db
class TestCellmlModelForm:
    def upload_file(self, tmp_path, file_name):
        test_file = os.path.join(settings.BASE_DIR, 'files', 'tests', file_name + ".cellml")
        cellml_file = file_name + str(uuid.uuid4()) + '.cellml.temp'
        temp_file = os.path.join(tmp_path, cellml_file)
        assert os.path.isfile(test_file)
        copyfile(test_file, temp_file)
        assert os.path.isfile(temp_file)

        tempfile = TemporaryUploadedFile(cellml_file, 'text/xml', os.path.getsize(test_file), 'utf-8')
        tempfile.file = open(temp_file, 'rb')
        return tempfile

    @pytest.fixture
    def file1(self, tmp_path):
        return self.upload_file(tmp_path, 'ohara_rudy_cipa_v1_2017')

    @pytest.fixture
    def file2(self, tmp_path):
        return self.upload_file(tmp_path, 'ohara_rudy_2011_epi')

    @pytest.fixture
    def file3(self, tmp_path):
        return self.upload_file(tmp_path, 'chaste-197x61')

    @pytest.fixture
    def file4(self, tmp_path):
        return self.upload_file(tmp_path, 'ohara_rudy_2011_epi_missing_unit')

    @pytest.fixture
    def data(self, admin_user):
        return {
            'author': admin_user,
            'predfeined': True,
            'name': "O'Hara-Rudy-CiPA",
            'description': 'human ventricular cell model (endocardial)',
            'version': 'v1.0',
            'year': 2017,
            'cellml_link': 'https://models.cellml.org/e/4e8/',
            'paper_link': 'https://www.ncbi.nlm.nih.gov/pubmed/28878692',
        }

    def test_non_admin(self, user):
        form = CellmlModelForm(user=user)
        assert 'ap_predict_model_call' not in form.fields
        assert 'predefined' not in form.fields

    def test_create(self, admin_user, data):
        assert not CellmlModel.objects.filter(name="O'Hara-Rudy-CiPA").exists()
        form = CellmlModelForm(user=admin_user, data=data)
        assert 'ap_predict_model_call' in form.fields
        assert 'predefined' in form.fields

        assert not form.is_valid()  # no call and no file
        data['ap_predict_model_call'] = '--model 1'
        form = CellmlModelForm(user=admin_user, data=data)
        assert not form.is_valid()  # --model in call
        data['ap_predict_model_call'] = '1'
        form = CellmlModelForm(user=admin_user, data=data)
        assert form.is_valid()
        model = form.save()
        assert model == CellmlModel.objects.get(name="O'Hara-Rudy-CiPA")

        # duplicate name not allowed
        form = CellmlModelForm(user=admin_user, data=data)
        assert not form.is_valid()

    def test_update(self, o_hara_model, data, admin_user):
        data['version'] = 'v2'
        form = CellmlModelForm(user=admin_user, instance=o_hara_model, data=data)
        form.is_valid()
        form.save()
        assert o_hara_model.version == 'v2'

    def test_file(self, data, file1, file2, admin_user, ion_currents):
        # file upload
        assert not CellmlModel.objects.filter(name="O'Hara-Rudy-CiPA").exists()
        assert not os.path.isfile(os.path.join(settings.MEDIA_ROOT, str(file1)))
        assert not os.path.isfile(os.path.join(settings.MEDIA_ROOT, str(file1)))
        form = CellmlModelForm(data, {'cellml_file': file1}, user=admin_user)
        assert form.is_valid(), str(form.errors)
        model = form.save()
        assert os.path.isfile(os.path.join(settings.MEDIA_ROOT, str(file1)))
        assert model == CellmlModel.objects.get(name="O'Hara-Rudy-CiPA")
        assert model.cellml_file == str(file1)
        # check ion currents are automatically assigned
        assert list(model.ion_currents.all()) == list(IonCurrent.objects.all())
        assert [str(c) for c in IonCurrent.objects.all()] == ['IKr (herg)', 'INa', 'ICaL', 'IKs', 'IK1', 'Ito', 'INaL']

        # change file
        form = CellmlModelForm(data, {'cellml_file': file2}, instance=model, user=admin_user)
        assert form.is_valid()
        form.save()
        assert not os.path.isfile(os.path.join(settings.MEDIA_ROOT, str(file1)))
        assert os.path.isfile(os.path.join(settings.MEDIA_ROOT, str(file2)))
        assert model.cellml_file == str(file2)
        # check ion currents are automatically assigned
        assert list(model.ion_currents.all()) == list(IonCurrent.objects.all())

        model.delete()
        assert not os.path.isfile(os.path.join(settings.MEDIA_ROOT, str(file2)))

    def test_both_call_and_file(self, o_hara_model, data, file1, admin_user):
        data['ap_predict_model_call'] = '1'
        form = CellmlModelForm(data, {'cellml_file': file1}, user=admin_user)
        assert not form.is_valid()

    def test_clear_file(self, o_hara_model, data, file1, admin_user):
        form = CellmlModelForm(data, {'cellml_file': file1}, instance=o_hara_model, user=admin_user)
        assert form.is_valid()
        assert form.save() == o_hara_model
        str(o_hara_model.cellml_file) == str(file1)

        form = CellmlModelForm(data, {'cellml_file': False}, instance=o_hara_model, user=admin_user)
        assert not form.is_valid()  # no call and no file

        data['ap_predict_model_call'] = '1'
        form = CellmlModelForm(data, {'cellml_file': False}, instance=o_hara_model, user=admin_user)
        assert form.is_valid()
        form.save()
        assert str(o_hara_model.cellml_file) == ''

    def test_wrong_file_type(self, data, file3, admin_user):
        form = CellmlModelForm(data, {'cellml_file': file3}, user=admin_user)
        assert not form.is_valid()  # This is an image not really an xml file
        assert "Unsupported file type, expecting a cellml file." in form.errors['cellml_file']

    def test_incorrect_cellml(self, data, file4, admin_user):
        form = CellmlModelForm(data, {'cellml_file': file4}, user=admin_user)
        assert not form.is_valid()  # This is an image not really an xml file
        assert "Could not process cellml model: \n    'Unknown unit <coulomb_per_mole>.'" in form.errors['cellml_file']

