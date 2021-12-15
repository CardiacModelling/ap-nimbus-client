import os
import shutil
import uuid

import pytest
from core.visibility import Visibility
from django.conf import settings
from files.models import CellmlModel


@pytest.mark.django_db
def test_CellmlModel_file(user):
    test_file1 = os.path.join(settings.BASE_DIR, 'files', 'tests', 'ohara_rudy_2011_epi.cellml')
    test_file2 = os.path.join(settings.BASE_DIR, 'files', 'tests', 'ohara_rudy_cipa_v1_2017.cellml')
    assert os.path.isfile(test_file1)
    assert os.path.isfile(test_file2)

    cellml_file1 = 'ohara_rudy_2011_epi' + str(uuid.uuid4()) + '.cellml'
    cellml_file2 = 'ohara_rudy_cipa_v1_2017' + str(uuid.uuid4()) + '.cellml'
    assert not os.path.isfile(os.path.join(settings.MEDIA_ROOT, cellml_file1))
    assert not os.path.isfile(os.path.join(settings.MEDIA_ROOT, cellml_file2))

    shutil.copy(test_file1, os.path.join(settings.MEDIA_ROOT, cellml_file1))
    shutil.copy(test_file2, os.path.join(settings.MEDIA_ROOT, cellml_file2))
    assert os.path.isfile(os.path.join(settings.MEDIA_ROOT, cellml_file1))
    assert os.path.isfile(os.path.join(settings.MEDIA_ROOT, cellml_file2))

    model = CellmlModel.objects.create(
        name="O'Hara-Rudy-CiPA",
        description='human ventricular cell model (endocardial)',
        year=2017,
        author=user,
        visibility=Visibility.MODERATED,
        cellml_file=cellml_file1,
    )
    CellmlModel.objects.filter(name="O'Hara-Rudy-CiPA").exists()
    assert model.cellml_file
    assert model.cellml_file.path == os.path.join(settings.MEDIA_ROOT, cellml_file1)

    # check changing the file deletes the old one
    model.cellml_file = cellml_file2
    model.save()
    model.refresh_from_db()
    assert model.cellml_file.path == os.path.join(settings.MEDIA_ROOT, cellml_file2)
    assert not os.path.isfile(os.path.join(settings.MEDIA_ROOT, cellml_file1))
    assert os.path.isfile(os.path.join(settings.MEDIA_ROOT, cellml_file2))

    # check that after delete both model and cellml file are deleted
    model.delete()
    not CellmlModel.objects.filter(name="O'Hara-Rudy-CiPA").exists()
    assert not os.path.isfile(os.path.join(settings.MEDIA_ROOT, cellml_file2))

