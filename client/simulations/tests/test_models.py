import math

import pytest
from files.models import IonCurrent
from simulations.models import CompoundConcentrationPoint, Simulation, SimulationIonCurrentParam


@pytest.mark.django_db
def test_simulation_negLogM(simulation_range, simulation_points, simulation_pkdata,
                            user, admin_user, other_user, o_hara_model):
    assert str(simulation_range) == 'my simulation1'
    assert simulation_range.status == Simulation.Status.NOT_STARTED
    assert simulation_range.author == user
    assert simulation_range.model == o_hara_model
    assert simulation_range.pacing_frequency == 0.05
    assert simulation_range.maximum_pacing_time == 5
    assert simulation_range.ion_current_type == Simulation.IonCurrentType.PIC50
    assert Simulation.conversion(simulation_range.ion_units)(10) == 10
    assert simulation_range.ion_units == Simulation.IonCurrentUnits.negLogM
    assert simulation_range.pk_or_concs == Simulation.PkOptions.compound_concentration_range
    assert simulation_range.minimum_concentration == 0
    assert simulation_range.maximum_concentration == 100
    assert simulation_range.intermediate_point_count == '4'

    assert str(simulation_points) == 'my simulation2'
    assert str(simulation_pkdata) == 'my simulation3'


@pytest.mark.django_db
def test_simulation_M(simulation_range, simulation_points, simulation_pkdata,
                      user, admin_user, other_user, o_hara_model):
    simulation_range.ion_current_type = Simulation.IonCurrentType.IC50
    simulation_range.ion_units = Simulation.IonCurrentUnits.M
    assert str(simulation_range) == 'my simulation1'
    assert simulation_range.status == Simulation.Status.NOT_STARTED
    assert simulation_range.author == user
    assert simulation_range.model == o_hara_model
    assert simulation_range.pacing_frequency == 0.05
    assert simulation_range.maximum_pacing_time == 5
    assert Simulation.conversion(simulation_range.ion_units)(10) == - math.log10(10)
    assert simulation_range.pk_or_concs == Simulation.PkOptions.compound_concentration_range
    assert simulation_range.minimum_concentration == 0
    assert simulation_range.maximum_concentration == 100
    assert simulation_range.intermediate_point_count == '4'

    assert str(simulation_points) == 'my simulation2'
    assert str(simulation_pkdata) == 'my simulation3'


@pytest.mark.django_db
def test_simulation_µM(simulation_range, simulation_points, simulation_pkdata,
                       user, admin_user, other_user, o_hara_model):
    simulation_range.ion_current_type = Simulation.IonCurrentType.IC50
    simulation_range.ion_units = Simulation.IonCurrentUnits.µM
    assert str(simulation_range) == 'my simulation1'
    assert simulation_range.status == Simulation.Status.NOT_STARTED
    assert simulation_range.author == user
    assert simulation_range.model == o_hara_model
    assert simulation_range.pacing_frequency == 0.05
    assert simulation_range.maximum_pacing_time == 5
    assert Simulation.conversion(simulation_range.ion_units)(10) == - math.log10(1e-6 * 10)
    assert simulation_range.pk_or_concs == Simulation.PkOptions.compound_concentration_range
    assert simulation_range.minimum_concentration == 0
    assert simulation_range.maximum_concentration == 100
    assert simulation_range.intermediate_point_count == '4'

    assert str(simulation_points) == 'my simulation2'
    assert str(simulation_pkdata) == 'my simulation3'


@pytest.mark.django_db
def test_simulation_nM(simulation_range, simulation_points, simulation_pkdata,
                       user, admin_user, other_user, o_hara_model):
    simulation_range.ion_current_type == Simulation.IonCurrentType.IC50
    simulation_range.ion_units = Simulation.IonCurrentUnits.nM
    assert str(simulation_range) == 'my simulation1'
    assert simulation_range.status == Simulation.Status.NOT_STARTED
    assert simulation_range.author == user
    assert simulation_range.model == o_hara_model
    assert simulation_range.pacing_frequency == 0.05
    assert simulation_range.maximum_pacing_time == 5
    assert Simulation.conversion(simulation_range.ion_units)(10) == - math.log10(1e-9 * 10)
    assert simulation_range.pk_or_concs == Simulation.PkOptions.compound_concentration_range
    assert simulation_range.minimum_concentration == 0
    assert simulation_range.maximum_concentration == 100
    assert simulation_range.intermediate_point_count == '4'

    assert str(simulation_points) == 'my simulation2'
    assert str(simulation_pkdata) == 'my simulation3'


@pytest.mark.django_db
def test_SimulationIonCurrentParam(simulation_range):
    assert SimulationIonCurrentParam.objects.count() == 7
    ICaL = IonCurrent.objects.get(name='ICaL')
    param = SimulationIonCurrentParam.objects.get(ion_current=ICaL, simulation=simulation_range)
    assert str(param) == 'ICaL - my simulation1'
    assert param.current == 70
    assert param.hill_coefficient == 1
    assert param.saturation_level == 0
    assert param.spread_of_uncertainty == 0.15


@pytest.mark.django_db
def test_CompoundConcentrationPoint(simulation_points):
    assert CompoundConcentrationPoint.objects.count() == 10
    assert [pnt.concentration for pnt in CompoundConcentrationPoint.objects.filter(simulation=simulation_points)] ==\
        [24.9197, 25.85, 27.73, 35.8, 41.032, 42.949, 56.20, 62, 67.31, 72.27]
    assert str(CompoundConcentrationPoint.objects.all().first()) == 'my simulation1 - 24.9197'
