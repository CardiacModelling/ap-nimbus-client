import pytest
from accounts.models import User
from files.models import CellmlModel, IonCurrent
from simulations.models import Simulation, SimulationIonCurrentParam, CompoundConcentrationPoint
from model_bakery.recipe import Recipe, seq


@pytest.fixture
def cellml_model_recipe():
    return Recipe('CellmlModel', name=seq('my model'), description=seq('my descr'),
                  year=2021, predefined=True)


@pytest.fixture
def simulation_recipe():
    return Recipe('Simulation', title=seq('my simulation'))


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        email='admin@example.com',
        full_name='Admin User',
        institution='UCL',
        password='password',
    )


@pytest.fixture
def user():
    return User.objects.create_user(
        email='test@example.com',
        full_name='Test User',
        institution='UCL',
        password='password',
    )


@pytest.fixture
def other_user():
    return User.objects.create_user(
        email='other@example.com',
        full_name='Other User',
        institution='UCL',
        password='password',
    )


@pytest.fixture
def logged_in_user(client, user):
    client.login(username=user.email, password='password')
    return user


@pytest.fixture
def logged_in_admin(client, admin_user):
    client.login(username=admin_user.email, password='password')
    return admin_user


PREDEF_ION_CURRENTS = [
    {'name': 'IKr',
     'alternative_name': 'herg',
     'metadata_tags': "membrane_rapid_delayed_rectifier_potassium_current_conductance, "
                      "membrane_rapid_delayed_rectifier_potassium_current_conductance_scaling_factor",
     'default_hill_coefficient': 1,
     'default_saturation_level': 0,
     'default_spread_of_uncertainty': 0.18},

    {'name': 'INa',
     'metadata_tags': "membrane_fast_sodium_current_conductance,"
                      "membrane_fast_sodium_current_conductance_scaling_factor",
     'default_hill_coefficient': 1,
     'default_saturation_level': 0,
     'default_spread_of_uncertainty': 0.2},

    {'name': 'ICaL',
     'metadata_tags': "membrane_L_type_calcium_current_conductance,"
                      "membrane_L_type_calcium_current_conductance_scaling_factor",
     'default_hill_coefficient': 1,
     'default_saturation_level': 0,
     'default_spread_of_uncertainty': 0.15},

    {'name': 'IKs',
     'metadata_tags': "membrane_slow_delayed_rectifier_potassium_current_conductance,"
                      "membrane_slow_delayed_rectifier_potassium_current_conductance_scaling_factor",
     'default_hill_coefficient': 1,
     'default_saturation_level': 0,
     'default_spread_of_uncertainty': 0.17},

    {'name': 'IK1',
     'metadata_tags': "membrane_inward_rectifier_potassium_current_conductance,"
                      "membrane_inward_rectifier_potassium_current_conductance_scaling_factor",
     'default_hill_coefficient': 1,
     'default_saturation_level': 0,
     'default_spread_of_uncertainty': 0.18},

    {'name': 'Ito',
     'metadata_tags': "membrane_fast_transient_outward_current_conductance,"
                      "membrane_fast_transient_outward_current_conductance_scaling_factor,"
                      "membrane_transient_outward_current_conductance,"
                      "membrane_transient_outward_current_conductance_scaling_factor",
     'default_hill_coefficient': 1,
     'default_saturation_level': 0,
     'default_spread_of_uncertainty': 0.15},

    {'name': 'INaL',
     'metadata_tags': "membrane_persistent_sodium_current_conductance,"
                      "membrane_persistent_sodium_current_conductance_scaling_factor",
    'default_hill_coefficient': 1,
    'default_saturation_level': 0,
    'default_spread_of_uncertainty': 0.2},
]


@pytest.fixture
def ion_currents(user):
    for predef_current in PREDEF_ION_CURRENTS:
        IonCurrent.objects.create(author=user, **predef_current)
    return IonCurrent.objects.all()


@pytest.fixture
def o_hara_model(cellml_model_recipe, user, ion_currents):
    model = cellml_model_recipe.make(
        author=user,
        predefined=True,
        name="O'Hara-Rudy-CiPA",
        description='human ventricular cell model (endocardial)',
        version='v1.0',
        year=2017,
        cellml_link='https://models.cellml.org/e/4e8/',
        paper_link='https://www.ncbi.nlm.nih.gov/pubmed/28878692',
        cellml_file='OHara-Rudy-CiPA-v1.0.cellml',
    )
    model.ion_currents.set(IonCurrent.objects.all())
    model.save()
    return model



@pytest.fixture
def simulation_range(simulation_recipe, user, o_hara_model):
    sim = simulation_recipe.make(notes = 'some notes',
                                 author = user,
                                 model = o_hara_model,
                                 pacing_frequency = 0.05,
                                 maximum_pacing_time = 5,
                                 ion_current_type = Simulation.IonCurrentType.PIC50,
                                 ion_units = Simulation.IonCurrentUnits.negLogM,
                                 pk_or_concs = Simulation.PkOptions.compound_concentration_range,
                                 minimum_concentration = 0,
                                 maximum_concentration = 100,
                                 intermediate_point_count = '4',
                                 intermediate_point_log_scale = True)
    vals = [4.37, 44.716, 70, 45.3, 41.8, 13.4, 52.1]
    params = [{'current': v,
             'hill_coefficient': c['default_hill_coefficient'],
             'saturation_level': c['default_saturation_level'],
             'spread_of_uncertainty': c['default_spread_of_uncertainty']}
            for v, c in zip(vals, PREDEF_ION_CURRENTS)]
    for curr, param in zip(IonCurrent.objects.all(), params):
        SimulationIonCurrentParam.objects.create(simulation=sim, ion_current=curr, **param)
    return sim


@pytest.fixture
def simulation_points(simulation_recipe, user, o_hara_model):
    sim = simulation_recipe.make(notes = 'some notes',
                                 author = user,
                                 model = o_hara_model,
                                 pacing_frequency = 0.05,
                                 maximum_pacing_time = 5,
                                 ion_current_type = Simulation.IonCurrentType.IC50,
                                 ion_units = Simulation.IonCurrentUnits.M,
                                 pk_or_concs = Simulation.PkOptions.compound_concentration_points)
    points = [41.032, 42.949, 62, 35.8, 24.9197, 72.27, 25.85, 56.20, 27.73, 67.31]
    for conc in points:
        CompoundConcentrationPoint.objects.create(simulation=sim, concentration=conc)
    return sim


@pytest.fixture
def simulation_pkdata(simulation_recipe, user, o_hara_model):
    return simulation_recipe.make(notes = 'some notes',
                                  author = user,
                                  model = o_hara_model,
                                  pacing_frequency = 0.05,
                                  maximum_pacing_time = 5,
                                  ion_current_type = Simulation.IonCurrentType.IC50,
                                  ion_units = Simulation.IonCurrentUnits.M,
                                  pk_or_concs = Simulation.PkOptions.pharmacokinetics,
                                  PK_data = 'pk_data.tsv')
