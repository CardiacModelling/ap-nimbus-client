import pytest
from simulations.views import to_int
from simulations.models import Simulation


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

    def test_list(self, client, simulation_recipe, logged_in_user, user, o_hara_model):
        from simulations.models import Simulation
        simulation_recipe.make(author=logged_in_user, model=o_hara_model, _quantity=3)
        my_simulations = simulation_recipe.make(author=user,  model=o_hara_model, _quantity=3)

        response = client.get('/simulations/')
        assert response.status_code == 200
        assert set(response.context['object_list']) == set(response.context['object_list'])

#@pytest.mark.django_db
#class TestSimulationCreateView:
#
#@pytest.mark.django_db
#class TestSimulationEditView:
#
#@pytest.mark.django_db
#class TestSimulationResultView:
#
@pytest.mark.django_db
class TestSimulationDeleteView:
    def test_owner_can_delete(self, logged_in_user, client, simulation_range):
        assert Simulation.objects.count() == 1
        response = client.post('/simulations/%d/delete' % simulation_range.pk)
        assert response.status_code == 302
        assert Simulation.objects.count() == 0

    def test_admin_can_delete(self, logged_in_admin, client, simulation_range):
        assert Simulation.objects.count() == 1
        simulation_range.author = logged_in_admin
        simulation_range.save()
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

