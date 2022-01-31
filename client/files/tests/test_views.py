import pytest
from files.models import CellmlModel


@pytest.mark.django_db
def test_CellmlModelListView(logged_in_user, other_user, admin_user, client, cellml_model_recipe):
    models = cellml_model_recipe.make(author=logged_in_user, _quantity=3)
    predef_models = cellml_model_recipe.make(author=other_user, _quantity=3, predefined=True)
    cellml_model_recipe.make(author=other_user, _quantity=3, predefined=False)  # uploaded (private) models

    response = client.get('/files/models/')
    assert response.status_code == 200
    assert set(response.context['object_list']) == set(models + predef_models)


@pytest.mark.django_db
class TestCellmlModelCreateView:
    def test_create_page_not_logged_in(self, user, client):
        response = client.get('/files/models/new/')
        assert response.status_code == 302

    def test_create_page_loads(self, logged_in_user, client):
        response = client.get('/files/models/new/')
        assert response.status_code == 200

    def test_create_cellml_model(self, logged_in_admin, client):
        assert CellmlModel.objects.count() == 0
        data = {
            'predefined': True,
            'name': "O'Hara-Rudy-CiPA",
            'description': 'human ventricular cell model (endocardial)',
            'version': 'v1.0',
            'year': 2017,
            'cellml_link': 'https://models.cellml.org/e/4e8/',
            'paper_link': 'https://www.ncbi.nlm.nih.gov/pubmed/28878692',
            'ap_predict_model_call': '8',
        }
        response = client.post('/files/models/new/', data=data)
        assert response.status_code == 302
        assert CellmlModel.objects.count() == 1


@pytest.mark.django_db
def test_CellmlModelUpdateView(logged_in_admin, client, cellml_model_recipe):
    model = cellml_model_recipe.make(
        author=logged_in_admin,
        predefined=True,
        name="O'Hara-Rudy-CiPA",
        description='human ventricular cell model (endocardial)',
        version='v1.0',
        year=2017,
        cellml_link='https://models.cellml.org/e/4e8/',
        paper_link='https://www.ncbi.nlm.nih.gov/pubmed/28878692',
        ap_predict_model_call='8',
    )
    assert CellmlModel.objects.count() == 1
    data = {
        'predefined': model.predefined,
        'name': 'new test name',
        'description': model.description,
        'version': model.version,
        'year': model.year,
        'cellml_link': model.cellml_link,
        'paper_link': model.paper_link,
        'ap_predict_model_call': model.ap_predict_model_call,
    }
    assert CellmlModel.objects.count() == 1
    response = client.post('/files/models/%d/edit/' % model.pk, data=data)
    assert response.status_code == 302
    model.refresh_from_db()
    assert CellmlModel.objects.count() == 1
    assert model.name == 'new test name'


@pytest.mark.django_db
class TestCellmlModelDetailView:
    def test_non_loged_in_cannot_see(self, user, client, o_hara_model):
        response = client.get('/files/models/%d/' % o_hara_model.pk)
        assert response.status_code == 302

    def test_non_owner_cannot_see_non_predef(self, logged_in_user, other_user, client, cellml_model_recipe):
        model = cellml_model_recipe.make(author=other_user, predefined=False)
        response = client.get('/files/models/%d/' % model.pk)
        assert response.status_code == 403

    def test_non_owner_can_see_predef(self, logged_in_user, other_user, client, cellml_model_recipe):
        model = cellml_model_recipe.make(author=other_user, predefined=True)
        response = client.get('/files/models/%d/' % model.pk)
        assert response.status_code == 200

    def test_admin_can_see_non_predef_non_owner(self, logged_in_admin, other_user, client, cellml_model_recipe):
        model = cellml_model_recipe.make(author=other_user, predefined=False)
        response = client.get('/files/models/%d/' % model.pk)
        assert response.status_code == 200


@pytest.mark.django_db
class TestCellmlModelDeleteView:
    def test_owner_can_delete(self, logged_in_user, client, o_hara_model):
        assert CellmlModel.objects.count() == 1
        response = client.post('/files/models/%d/delete/' % o_hara_model.pk)
        assert response.status_code == 302
        assert CellmlModel.objects.count() == 0

    def test_admin_can_delete(self, logged_in_admin, client, o_hara_model):
        assert CellmlModel.objects.count() == 1
        response = client.post('/files/models/%d/delete/' % o_hara_model.pk)
        assert response.status_code == 302
        assert CellmlModel.objects.count() == 0

    def test_non_owner_cannot_delete(self, logged_in_user, other_user, client, cellml_model_recipe):
        model = cellml_model_recipe.make(author=other_user)
        assert CellmlModel.objects.count() == 1
        response = client.post('/stories/%d/delete' % model.pk)
        assert response.status_code == 404

    def test_non_logged_in_owner_cannot_delete(self, user, client, o_hara_model):
        assert CellmlModel.objects.count() == 1
        response = client.post('/files/models/%d/delete/' % o_hara_model.pk)
        assert response.status_code == 403

