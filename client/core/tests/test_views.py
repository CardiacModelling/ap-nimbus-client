import filecmp
import os
import shutil

import pytest
from django.conf import settings
from django.http import FileResponse


@pytest.mark.django_db
def test_media_root(logged_in_user, client):
    # the url patterns assume /media is used, so don't change it
    assert settings.MEDIA_URL == (settings.FORCE_SCRIPT_NAME + '/media/').replace('//', '/')


@pytest.mark.django_db
def test_not_logged_in(user, client):
    response = client.get('/media/somefile.cellml')
    assert response.status_code == 302


@pytest.mark.django_db
def test_not_a_file(logged_in_user, client):
    response = client.get('/media/somefile.cellml')
    assert response.status_code == 403


@pytest.mark.django_db
def test_not_the_author(other_user, client, simulation_pkdata):
    client.login(username=other_user.email, password='password')
    assert simulation_pkdata.author != other_user
    response = client.get(f'/media/{simulation_pkdata.PK_data}')
    assert response.status_code == 403


@pytest.mark.django_db
def test_is_author(logged_in_user, client, simulation_pkdata, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    assert simulation_pkdata.author == logged_in_user
    # copy pk data file
    pkd_test_source_file = os.path.join(settings.BASE_DIR, 'simulations', 'tests', 'small_sample.tsv')
    pkd_test_dest_file = os.path.join(settings.MEDIA_ROOT, str(simulation_pkdata.PK_data))
    shutil.copy(pkd_test_source_file, pkd_test_dest_file)
    assert os.path.isfile(pkd_test_dest_file)

    # request file via view
    response = client.get(f'/media/{simulation_pkdata.PK_data}')
    assert response.status_code == 200
    assert isinstance(response, FileResponse)

    # dump results test file
    response_file_path = os.path.join(tmp_path, str(simulation_pkdata.PK_data))
    with open(response_file_path, 'wb') as file:
        file.write(b''.join(response.streaming_content))
    assert filecmp.cmp(pkd_test_dest_file, response_file_path, shallow=False)
