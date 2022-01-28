import os
import shutil
import uuid

import pytest
from django.conf import settings
from simulations.models import Simulation


@pytest.mark.django_db
def test_auto_delete_file_on_delete(simulation_pkdata):
    assert Simulation.objects.count() == 1
    sample = os.path.join(settings.BASE_DIR, 'simulations', 'tests', 'Sample2.tsv')
    assert os.path.isfile(sample)

    uploaded = 'Sample' + str(uuid.uuid4()) + '.tsv'
    shutil.copy(sample, os.path.join(settings.MEDIA_ROOT, uploaded))
    assert os.path.isfile(os.path.join(settings.MEDIA_ROOT, uploaded))

    simulation_pkdata.PK_data = uploaded
    simulation_pkdata.save()
    simulation_pkdata.delete()
    assert not os.path.isfile(os.path.join(settings.MEDIA_ROOT, uploaded))
    assert Simulation.objects.count() == 0


@pytest.mark.django_db
def test_auto_delete_file_on_delete_file_not_exist(simulation_pkdata):
    assert Simulation.objects.count() == 1
    assert not os.path.isfile(simulation_pkdata.PK_data.path)
    simulation_pkdata.delete()
    assert Simulation.objects.count() == 0


@pytest.mark.django_db
def test_auto_delete_file_on_delete_no_file_set(simulation_range):
    assert Simulation.objects.count() == 1
    assert not simulation_range.PK_data
    simulation_range.delete()
    assert Simulation.objects.count() == 0
