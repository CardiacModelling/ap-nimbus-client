from django import template
from files.models import IonCurrent
from simulations.models import SimulationIonCurrentParam


register = template.Library()


@register.simple_tag
def num_ion_currents_p1():
    return IonCurrent.objects.count() + 1


@register.simple_tag
def ion_currents():
    return IonCurrent.objects.all()


@register.simple_tag
def simulation_ion_currents(simulation):
    current_params = []
    for current in IonCurrent.objects.all():
        current_param = SimulationIonCurrentParam.objects.filter(simulation=simulation, ion_current=current)
        if current_param.exists():
            current_params.append(str(current_param.first().current))
        else:
            current_params.append('')
    return current_params


@register.simple_tag
def short_field_name(field_name):
    return field_name.split('_')[-1]
