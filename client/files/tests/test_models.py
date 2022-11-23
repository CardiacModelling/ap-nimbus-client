import httpx
import pytest
from files.models import AppredictLookupTableManifest, CellmlModel, IonCurrent


@pytest.mark.django_db
def test_CellmlModel_predef(o_hara_model, user, other_user, admin_user):
    assert CellmlModel.objects.filter(name=o_hara_model.name).exists()
    assert o_hara_model.author == user
    assert o_hara_model.predefined
    assert o_hara_model.name == "O'Hara-Rudy-CiPA"
    assert o_hara_model.description == 'human ventricular cell model (endocardial)'
    assert o_hara_model.version == 'v1.0'
    assert o_hara_model.year == 2017
    assert o_hara_model.cellml_link == 'https://models.cellml.org/e/4e8/'
    assert o_hara_model.paper_link == 'https://www.ncbi.nlm.nih.gov/pubmed/28878692'
    assert o_hara_model.ap_predict_model_call == '6'
    assert not o_hara_model.cellml_file
    assert str(o_hara_model) == "O'Hara-Rudy-CiPA v1.0 (2017)"
    o_hara_model.delete()
    assert not CellmlModel.objects.filter(name=o_hara_model.name).exists()


@pytest.mark.django_db
def test_CellmlModel_uploaded(o_hara_model, user, other_user, admin_user):
    o_hara_model.predefined = False
    o_hara_model.ap_predict_model_call = '8'
    o_hara_model.cellml_file = None
    o_hara_model.save()
    assert CellmlModel.objects.filter(name=o_hara_model.name).exists()
    assert not o_hara_model.predefined
    assert o_hara_model.ap_predict_model_call == '8'
    assert str(o_hara_model.cellml_file) == ''
    o_hara_model.delete()
    assert not CellmlModel.objects.filter(name=o_hara_model.name).exists()


@pytest.mark.django_db
def test_CellmlModel_uploaded2(o_hara_model, user, other_user, admin_user):
    o_hara_model.predefined = False
    o_hara_model.cellml_file = 'cellml_file_name.cellml'
    o_hara_model.save()
    assert CellmlModel.objects.filter(name=o_hara_model.name).exists()
    assert not o_hara_model.predefined
    assert str(o_hara_model.cellml_file) == 'cellml_file_name.cellml'
    o_hara_model.delete()
    assert not CellmlModel.objects.filter(name=o_hara_model.name).exists()


@pytest.mark.django_db
def test_CellmlModel_uploaded3(o_hara_model, user, other_user, admin_user):
    o_hara_model.author = user
    o_hara_model.predefined = False
    o_hara_model.cellml_file = 'cellml_file_name.cellml'
    o_hara_model.save()
    assert CellmlModel.objects.filter(name=o_hara_model.name).exists()
    assert not o_hara_model.predefined
    assert str(o_hara_model.cellml_file) == 'cellml_file_name.cellml'
    o_hara_model.cellml_file = 'some_other_file_name.cellml'
    o_hara_model.save()
    o_hara_model.refresh_from_db()
    assert str(o_hara_model.cellml_file) == 'some_other_file_name.cellml'


@pytest.mark.django_db
def test_IonCurrent(user):
    assert IonCurrent.objects.count() == 0
    IonCurrent.objects.create(author=user, name='INaL', default_hill_coefficient=1, default_saturation_level=0,
                              metadata_tags="membrane_persistent_sodium_current_conductance, "
                                            "membrane_persistent_sodium_current_conductance_scaling_factor",
                              default_spread_of_uncertainty=0.2)
    assert IonCurrent.objects.count() == 1


@pytest.mark.django_db
def test_AppredictLookupTableManifest(httpx_mock, manifest_contents):
    expected_manifest = set(['tentusscher_model_2006_epi',
                             'paci_hyttinen_aaltosetala_severi_ventricularVersion',
                             'HundRudy2004_units',
                             'MahajanShiferaw2008_units',
                             'grandi_pasqualini_bers_2010_epi',
                             'ohara_rudy_cipa_v1_2017',
                             'ohara_rudy_2011_endo',
                             'shannon_wang_puglisi_weber_bers_2004_model_updated'])

    assert AppredictLookupTableManifest.objects.count() == 0

    # mock getting manifest file from cardiac server
    httpx_mock.add_response(text=manifest_contents)
    assert set(AppredictLookupTableManifest.get_manifest()) == expected_manifest
    assert AppredictLookupTableManifest.objects.count() == 1

    # calling again does not create more DB entries
    httpx_mock.add_response(text=manifest_contents)
    assert set(AppredictLookupTableManifest.get_manifest()) == expected_manifest
    assert AppredictLookupTableManifest.objects.count() == 1

    # fallback if url does not respond with status 200
    httpx_mock.add_response(status_code=404)
    assert set(AppredictLookupTableManifest.get_manifest()) == expected_manifest
    assert AppredictLookupTableManifest.objects.count() == 1

    # fallback on httpx error
    httpx_mock.add_exception(httpx.ReadTimeout("Unable to read within timeout"))
    assert set(AppredictLookupTableManifest.get_manifest()) == expected_manifest
    assert AppredictLookupTableManifest.objects.count() == 1
