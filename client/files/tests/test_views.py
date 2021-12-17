import pytest
from core import recipes
from core.visibility import Visibility
from files.models import CellmlModel


@pytest.mark.django_db
class TestCellmlModelListView:
    def test_ListView(self, logged_in_user, other_user, admin_user, client):
        models = recipes.cellml_model.make(author=logged_in_user, _quantity=3)
        other_models = recipes.cellml_model.make(author=other_user, _quantity=3, visibility=Visibility.PUBLIC)
        recipes.cellml_model.make(author=other_user, _quantity=3, visibility=Visibility.PRIVATE)  # private models
        moderated_models = recipes.cellml_model.make(author=admin_user, _quantity=3, visibility=Visibility.MODERATED)

        response = client.get('/files/models/')
        assert response.status_code == 200
        assert set(response.context['object_list']) == set(models + other_models + moderated_models)


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
            'visibility': Visibility.PUBLIC,
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
class TestCellmlModelUpdateView:
    def test_update(self, logged_in_admin, client):
        model = recipes.cellml_model.make(
            author=logged_in_admin,
            visibility=Visibility.PUBLIC,
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
            'visibility': model.visibility,
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

    def test_non_owner_cannot_see_private(self, logged_in_user, other_user, client):
        model = recipes.cellml_model.make(author=other_user, visibility=Visibility.PRIVATE)
        response = client.get('/files/models/%d/' % model.pk)
        assert response.status_code == 403

    def test_non_owner_cannot_see_public(self, logged_in_user, other_user, client):
        model = recipes.cellml_model.make(author=other_user, visibility=Visibility.PUBLIC)
        response = client.get('/files/models/%d/' % model.pk)
        assert response.status_code == 200

    def test_admin_can_see_private(self, logged_in_admin, other_user, client):
        model = recipes.cellml_model.make(author=other_user, visibility=Visibility.PRIVATE)
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

    def test_non_owner_cannot_delete(self, logged_in_user, other_user, client):
        model = recipes.cellml_model.make(author=other_user)
        assert CellmlModel.objects.count() == 1
        response = client.post('/stories/%d/delete' % model.pk)
        assert response.status_code == 404

    def test_non_logged_in_owner_cannot_delete(self, user, client, o_hara_model):
        assert CellmlModel.objects.count() == 1
        response = client.post('/files/models/%d/delete/' % o_hara_model.pk)
        assert response.status_code == 403

