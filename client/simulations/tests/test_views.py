import pytest
from files.models import IonCurrent
from simulations.models import Simulation
from simulations.views import to_int


@pytest.mark.django_db
def test_to_int():
    assert to_int(12.4) == 12.4
    assert to_int(5.0) == 5
    assert str(to_int(5.0)) == '5'


@pytest.mark.django_db
class TestSimulationListView:
    def test_not_logged_in(self, client):
        response = client.get('/simulations/')
        assert response.status_code == 302

    def test_list(self, client, simulation_recipe, logged_in_user, other_user, o_hara_model):
        simulation_recipe.make(author=other_user, model=o_hara_model, _quantity=3)
        my_simulations = simulation_recipe.make(author=logged_in_user, model=o_hara_model, _quantity=3)

        response = client.get('/simulations/')
        assert response.status_code == 200
        assert set(response.context['object_list']) == set(my_simulations)


@pytest.mark.django_db
class TestSimulationCreateView_andTemplateView:
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

    def test_create_page_not_logged_in(self, user, client):
        response = client.get('/simulations/new')
        assert response.status_code == 302

    def test_template_page_not_logged_in(self, user, client, simulation_range):
        response = client.get('/simulations/%s/template' % simulation_range.pk)
        assert response.status_code == 302

    def test_can_create(self, logged_in_user, client, new_sim_data):
        assert IonCurrent.objects.count() == 7
        assert Simulation.objects.count() == 1
        response = client.post('/simulations/new', new_sim_data)
        assert response.status_code == 302
        assert Simulation.objects.count() == 2

    def test_template_can_create(self, logged_in_user, client, new_sim_data, simulation_range):
        assert IonCurrent.objects.count() == 7
        assert Simulation.objects.count() == 1
        response = client.post('/simulations/%s/template' % simulation_range.pk, new_sim_data)
        assert response.status_code == 302
        assert Simulation.objects.count() == 2

    def test_cannot_duplicate_title(self, logged_in_user, client, new_sim_data, simulation_range):
        assert Simulation.objects.count() == 1
        new_sim_data['title'] = simulation_range.title
        response = client.post('/simulations/new', data=new_sim_data)
        assert response.status_code == 200
        assert Simulation.objects.count() == 1
        simulation_range.refresh_from_db()
        assert simulation_range.notes != new_sim_data['notes']

    def test_template_cannot_duplicate_title(self, logged_in_user, client, new_sim_data, simulation_range):
        assert Simulation.objects.count() == 1
        new_sim_data['title'] = simulation_range.title
        response = client.post('/simulations/%s/template' % simulation_range.pk, data=new_sim_data)
        assert response.status_code == 200
        assert Simulation.objects.count() == 1
        simulation_range.refresh_from_db()
        assert simulation_range.notes != new_sim_data['notes']


@pytest.mark.django_db
class TestSimulationEditView:
    def test_not_logged_in(self, client, user, simulation_range):
        response = client.get('/simulations/%d/edit' % simulation_range.pk)
        assert response.status_code == 302

    def test_non_owner_cannot_edit(self, other_user, client, simulation_range):
        client.login(username=other_user.email, password='password')
        response = client.get('/simulations/%d/edit' % simulation_range.pk)
        assert response.status_code == 403

    def test_cannot_duplicate_title(self, logged_in_user, client, simulation_recipe, simulation_range, o_hara_model):
        assert simulation_range.author == logged_in_user
        new_simulation = simulation_recipe.make(author=logged_in_user, model=o_hara_model)
        assert new_simulation.title != simulation_range.title
        data = {'title': new_simulation.title, 'notes': 'new notes'}
        response = client.post('/simulations/%d/edit' % simulation_range.pk, data=data)
        assert response.status_code == 200
        simulation_range.refresh_from_db()
        assert new_simulation.title != simulation_range.title

    def test_owner_can_edit(self, logged_in_user, client, simulation_range):
        assert simulation_range.author == logged_in_user
        data = {'title': 'new title', 'notes': 'new notes'}
        response = client.post('/simulations/%d/edit' % simulation_range.pk, data=data)
        assert response.status_code == 302
        simulation_range.refresh_from_db()
        assert simulation_range.title == data['title']
        assert simulation_range.notes == data['notes']


@pytest.mark.django_db
class TestSimulationResultView:
    def test_non_loged_in_cannot_see(self, user, client, simulation_range):
        response = client.get('/simulations/%d/result' % simulation_range.pk)
        assert response.status_code == 302

    def test_non_owner_cannot_see(self, other_user, client, simulation_range):
        client.login(username=other_user.email, password='password')
        assert simulation_range.author != other_user
        response = client.get('/simulations/%d/result' % simulation_range.pk)
        assert response.status_code == 403

    def test_owner_can_see(self, logged_in_user, client, cellml_model_recipe, simulation_range):
        assert simulation_range.author == logged_in_user
        response = client.get('/simulations/%d/result' % simulation_range.pk)
        assert response.status_code == 200


@pytest.mark.django_db
class TestSimulationDeleteView:
    def test_owner_can_delete(self, logged_in_user, client, simulation_range):
        assert Simulation.objects.count() == 1
        response = client.post('/simulations/%d/delete' % simulation_range.pk)
        assert response.status_code == 302
        assert Simulation.objects.count() == 0

    def test_non_owner_cannot_delete(self, other_user, client, simulation_range):
        client.login(username=other_user.email, password='password')
        assert simulation_range.author != other_user
        assert Simulation.objects.count() == 1
        response = client.post('/simulations/%d/delete' % simulation_range.pk)
        assert response.status_code == 403

    def test_non_logged_in_owner_cannot_delete(self, user, client, simulation_range):
        assert simulation_range.author == user
        assert Simulation.objects.count() == 1
        response = client.post('/simulations/%d/delete' % simulation_range.pk)
        assert response.status_code == 403

