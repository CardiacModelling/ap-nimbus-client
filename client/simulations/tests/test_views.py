import pytest
from simulations.views import test_to_int


@pytest.mark.django_db
def test_to_int():
    assert test_to_int('bla') == 'bla'
    assert test_to_int(12.4) == 12.4
    assert test_to_int(5.0) == 5
    assert str(test_to_int(5.0)) == '5'


@pytest.mark.django_db
def estSimulationListView:
    def test_not_logged_in(self, client):
        response = client.get('/simulations/')
        assert response.status_code == 403

    def test_list(self, client, simulation_recipe, logged_in_user, user):
        simulation_recipe.make(author=user, _quantity=3)
        simulations = simulation_recipe.make(author=logged_in_user, _quantity=3)

        response = client.get('/files/models/')
        assert response.status_code == 200
        assert set(response.context['object_list']) == set(simulations)

#@pytest.mark.django_db
#class TestSimulationCreateView:
#
#@pytest.mark.django_db
#class TestSimulationEditView:
#
#@pytest.mark.django_db
#class TestSimulationResultView:
#
#@pytest.mark.django_db
#class TestSimulationDeleteView
#
