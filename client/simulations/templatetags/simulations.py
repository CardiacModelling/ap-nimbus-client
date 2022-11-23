from django import template
from files.models import IonCurrent
from simulations.models import CompoundConcentrationPoint, Simulation, SimulationIonCurrentParam


register = template.Library()


@register.simple_tag
def ion_currents():
    """
    All ion currents.
    """
    return IonCurrent.objects.all().order_by('pk')


@register.simple_tag
def simulation_ion_current(simulation, current):
    """
    The value this simulation has for the given current or '' if it doesn't have a value.
    """
    try:
        return SimulationIonCurrentParam.objects.get(simulation=simulation, ion_current=current)
    except SimulationIonCurrentParam.DoesNotExist:
        return ''


@register.simple_tag
def print_compound_concentrations(simulation):
    if simulation.pk_or_concs == Simulation.PkOptions.compound_concentration_range:
        min_max_range = str(simulation.minimum_concentration) + ' - ' + str(simulation.maximum_concentration) + ' (µM)'
        return (min_max_range, min_max_range)

    elif simulation.pk_or_concs == Simulation.PkOptions.compound_concentration_points:
        points = [p.concentration for p in CompoundConcentrationPoint.objects.filter(simulation=simulation)]
        points_range = str(points) if len(points) <= 2 else '[' + str(points[0]) + ' ... ' + str(points[-1]) + ']'
        return (str(points) + ' (µM)', points_range + ' (µM)')

    else:
        file_name = str(simulation.PK_data)
        truncated = file_name[:20] + '...' if len(file_name) > 23 else file_name
        return ('Compound concentrations from TSV file: %s.' % file_name, truncated)


@register.simple_tag
def short_field_name(field_name):
    return field_name.split('_')[-1].title()


@register.simple_tag
def print_field_name(field_name):
    return field_name.replace('_', ' ').title()
