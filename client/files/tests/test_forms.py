import os
import uuid

import pytest
from core.visibility import Visibility
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from files.forms import CellmlModelForm
from files.models import CellmlModel


@pytest.mark.django_db
class TestCellmlModelForm:
    def upload_file(self, file_name):
        test_file = os.path.join(settings.BASE_DIR, 'files', 'tests', file_name + ".cellml")
        assert os.path.isfile(test_file)

        cellml_file = file_name + str(uuid.uuid4()) + '.cellml'
        file_data = None
        with open(test_file, 'rb') as f:
            file_data = f.read()
        return SimpleUploadedFile(cellml_file, file_data)

    @pytest.fixture
    def file1(self):
        return self.upload_file('ohara_rudy_cipa_v1_2017')

    @pytest.fixture
    def file2(self):
        return self.upload_file('ohara_rudy_2011_epi')

    @pytest.fixture
    def file3(self):
        return self.upload_file('chaste-197x61')

    @pytest.fixture
    def data(self, admin_user):
        return {
            'author': admin_user,
            'visibility': Visibility.PUBLIC,
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
        assert str(form.fields['visibility'].choices) == "[('public', 'Public'), ('private', 'Private')]"

    def test_create(self, admin_user, data):
        assert not CellmlModel.objects.filter(name="O'Hara-Rudy-CiPA").exists()
        form = CellmlModelForm(user=admin_user, data=data)
        assert 'ap_predict_model_call' in form.fields
        assert str(form.fields['visibility'].choices) == \
            "[('public', 'Public'), ('moderated', 'Moderated'), ('private', 'Private')]"

        assert not form.is_valid()  # no call and no file
        data['ap_predict_model_call'] = '--model 1'
        form = CellmlModelForm(user=admin_user, data=data)
        assert not form.is_valid()  # --model in call
        data['ap_predict_model_call'] = '1'
        form = CellmlModelForm(user=admin_user, data=data)
        assert form.is_valid()
        model = form.save()
        assert model == CellmlModel.objects.get(name="O'Hara-Rudy-CiPA")

    def test_update(self, o_hara_model, data, admin_user):
        data['name'] = 'changed model'
        form = CellmlModelForm(user=admin_user, instance=o_hara_model, data=data)
        form.is_valid()
        form.save()
        assert o_hara_model.name == 'changed model'

    def test_file(self, data, file1, file2, admin_user):
        # file upload
        assert not CellmlModel.objects.filter(name="O'Hara-Rudy-CiPA").exists()
        assert not os.path.isfile(os.path.join(settings.MEDIA_ROOT, str(file1)))
        assert not os.path.isfile(os.path.join(settings.MEDIA_ROOT, str(file1)))
        form = CellmlModelForm(data, {'cellml_file': file1}, user=admin_user)
        assert form.is_valid()
        model = form.save()
        assert os.path.isfile(os.path.join(settings.MEDIA_ROOT, str(file1)))
        assert model == CellmlModel.objects.get(name="O'Hara-Rudy-CiPA")
        assert model.cellml_file == str(file1)

        # change file
        form = CellmlModelForm(data, {'cellml_file': file2}, instance=model, user=admin_user)
        assert form.is_valid()
        form.save()
        assert not os.path.isfile(os.path.join(settings.MEDIA_ROOT, str(file1)))
        assert os.path.isfile(os.path.join(settings.MEDIA_ROOT, str(file2)))
        assert model.cellml_file == str(file2)

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
