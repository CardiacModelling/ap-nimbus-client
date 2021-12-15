import pytest
from core.visibility import Visibility
from files.models import CellmlModel


@pytest.mark.django_db
def test_CellmlModel_public(o_hara_model, user, other_user, admin_user):
    assert CellmlModel.objects.filter(name=o_hara_model.name).exists()
    assert o_hara_model.author == user
    assert o_hara_model.visibility == Visibility.PUBLIC
    assert o_hara_model.name == "O'Hara-Rudy-CiPA"
    assert o_hara_model.description == 'human ventricular cell model (endocardial)'
    assert o_hara_model.version == 'v1.0'
    assert o_hara_model.year == 2017
    assert o_hara_model.cellml_link == 'https://models.cellml.org/e/4e8/'
    assert o_hara_model.paper_link == 'https://www.ncbi.nlm.nih.gov/pubmed/28878692'
    assert o_hara_model.ap_predict_model_call is None
    assert o_hara_model.cellml_file == 'OHara-Rudy-CiPA-v1.0.cellml'
    assert user in o_hara_model.viewers
    assert other_user in o_hara_model.viewers
    assert admin_user in o_hara_model.viewers
    assert o_hara_model.is_editable_by(user)
    assert not o_hara_model.is_editable_by(other_user)
    assert o_hara_model.is_editable_by(admin_user)
    assert str(o_hara_model) == "O'Hara-Rudy-CiPA v1.0 (2017)"
    o_hara_model.delete()
    assert not CellmlModel.objects.filter(name=o_hara_model.name).exists()


@pytest.mark.django_db
def test_CellmlModel_private(o_hara_model, user, other_user, admin_user):
    o_hara_model.visibility = Visibility.PRIVATE
    o_hara_model.ap_predict_model_call = '8'
    o_hara_model.cellml_file = None
    o_hara_model.save()
    assert CellmlModel.objects.filter(name=o_hara_model.name).exists()
    assert o_hara_model.visibility == Visibility.PRIVATE
    assert o_hara_model.ap_predict_model_call == '8'
    assert o_hara_model.cellml_file is None
    assert user in o_hara_model.viewers
    assert other_user not in o_hara_model.viewers
    assert admin_user in o_hara_model.viewers
    assert o_hara_model.is_editable_by(user)
    assert not o_hara_model.is_editable_by(other_user)
    assert o_hara_model.is_editable_by(admin_user)
    o_hara_model.delete()
    assert not CellmlModel.objects.filter(name=o_hara_model.name).exists()


@pytest.mark.django_db
def test_CellmlModel_moderated(o_hara_model, user, other_user, admin_user):
    o_hara_model.visibility = Visibility.MODERATED
    o_hara_model.save()
    assert o_hara_model.visibility == Visibility.MODERATED
    assert user in o_hara_model.viewers
    assert other_user in o_hara_model.viewers
    assert admin_user in o_hara_model.viewers
    assert o_hara_model.is_editable_by(user)
    assert not o_hara_model.is_editable_by(other_user)
    assert o_hara_model.is_editable_by(admin_user)
