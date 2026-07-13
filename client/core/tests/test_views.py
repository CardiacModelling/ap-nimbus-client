import filecmp
import os
import shutil

import pytest
from django.conf import settings
from django.http import FileResponse
from django.test import override_settings
from django.urls import reverse


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
    assert simulation_pkdata.author == logged_in_user
    # override_settings scopes MEDIA_ROOT to this test and restores it on exit,
    # so the tmp_path never leaks into the global settings object.
    with override_settings(MEDIA_ROOT=tmp_path):
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


@pytest.mark.django_db
@pytest.mark.parametrize('page,surrounding_text', [
    ('home', 'registering for an account'),
    ('privacy', 'you supply when you'),
])
def test_register_link_hidden_when_ldap_enabled(client, page, surrounding_text):
    # Registration can never succeed under LDAP, so the UI must not link to it.
    register_url = reverse('accounts:register')

    with override_settings(AP_PREDICT_LDAP=False):
        shown = client.get(reverse(page)).content.decode()
    assert register_url in shown
    assert surrounding_text in shown

    with override_settings(AP_PREDICT_LDAP=True):
        hidden = client.get(reverse(page)).content.decode()
    # The dead register link is gone, but the surrounding sentence text remains.
    assert register_url not in hidden
    assert surrounding_text in hidden
