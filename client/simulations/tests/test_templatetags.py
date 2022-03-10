import pytest
from files.models import IonCurrent
from simulations.models import Simulation, SimulationIonCurrentParam
from simulations.templatetags.simulations import (
    ion_currents,
    print_compound_concentrations,
    print_field_name,
    short_field_name,
    simulation_ion_current,
)


@pytest.mark.django_db
def test_ion_currents():
    assert len(ion_currents()) == ion_currents().count() == 0


@pytest.mark.django_db
def test_ion_currents_2(simulation_range):
    assert len(ion_currents()) == 7
    assert list(ion_currents()) == list(IonCurrent.objects.all())


@pytest.mark.django_db
def test_simulation_ion_current(simulation_range, simulation_points, simulation_pkdata):
    current = IonCurrent.objects.get(name='IKr')
    my_param = SimulationIonCurrentParam.objects.get(simulation=simulation_range, ion_current=current)
    assert simulation_ion_current(simulation_range, current) == my_param

    assert str(simulation_ion_current(simulation_points, current)) == ''
    new_param = SimulationIonCurrentParam.objects.create(simulation=simulation_points, ion_current=current)
    assert simulation_ion_current(simulation_points, current) == new_param

    assert str(simulation_ion_current(simulation_pkdata, current)) == ''
    new_param = SimulationIonCurrentParam.objects.create(simulation=simulation_pkdata, ion_current=current)
    assert simulation_ion_current(simulation_pkdata, current) == new_param


@pytest.mark.django_db
def test_print_compound_concentrations_range(simulation_range, simulation_points, simulation_pkdata):
    assert print_compound_concentrations(simulation_range) == ('0 - 100 (µM)', '0 - 100 (µM)')
    assert print_compound_concentrations(simulation_points) == \
        ('[24.9197, 25.85, 27.73, 35.8, 41.032, 42.949, 56.2, 62.0, 67.31, 72.27] (µM)', '[24.9197 ... 72.27] (µM)')
    assert simulation_pkdata.PK_data.path.endswith('pk_data.tsv')
    assert print_compound_concentrations(simulation_pkdata) == \
        (f'Compound concentrations from TSV file: {simulation_pkdata.PK_data}.',
         f'{str(simulation_pkdata.PK_data)[:20]}...')


@pytest.mark.django_db
def test_short_field_name():
    assert short_field_name('compound_concentration_range') == 'Range'
    assert short_field_name('compound_concentration_points') == 'Points'
    assert short_field_name('pharmacokinetics') == 'Pharmacokinetics'
    assert short_field_name('') == ''


@pytest.mark.django_db
def test_print_field_name():
    for choice in Simulation.PkOptions.choices:
        assert print_field_name(choice[0]) == choice[1], str(choice[0]) + '\n' + str(choice[1])
