from braces.forms import UserKwargModelFormMixin
from cellmlmanip import load_model
from django import forms

from files.models import CellmlModel, IonCurrent
from .models import Simulation, SimulationIonCurrentParam
from django.forms import inlineformset_factory



class BaseSimulationFormSet(forms.BaseFormSet):
    def save(self, simulation=None, **kwargs):
        return [form.save(simulation=simulation, **kwargs) for form in self.forms]


class IonCurrentForm(forms.ModelForm, UserKwargModelFormMixin):# max/min val for floats
    class Meta:
        model = SimulationIonCurrentParam
        exclude = ('author', 'simulation')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
#        assert False, str(self.initial['ion_current'])
        self.fields['ion_current'].widget = forms.HiddenInput()
        self.fields['hill_coefficient'].widget.attrs['min'] = 0.1
        self.fields['hill_coefficient'].widget.attrs['max'] = 5.0
        self.fields['hill_coefficient'].widget.attrs['step'] = 0.1

        self.fields['saturation_level'].widget.attrs['min'] = 0.0
        self.fields['saturation_level'].widget.attrs['step'] = 1.0

        self.fields['spread_of_uncertainty'].widget.attrs['min'] = 0.0
        self.fields['spread_of_uncertainty'].widget.attrs['max'] = 2.0
        self.fields['spread_of_uncertainty'].widget.attrs['step'] = 0.01

    def clean_spread_of_uncertainty(self):
        spread_of_uncertainty = self.cleaned_data['spread_of_uncertainty']
        if spread_of_uncertainty <= 0:
            raise forms.ValidationError('Spread of uncertainty cannot be 0.')
        return spread_of_uncertainty

    def save(self, simulation=None, **kwargs):
        pass

IonCurrentFormSet = inlineformset_factory(
    parent_model=Simulation,
    model=SimulationIonCurrentParam,
    form=IonCurrentForm,
    formset=BaseSimulationFormSet,
    exclude=('author', 'simulation'),
    can_delete=False,
    can_order=False,
    extra=0,
    min_num=0,
)


class SimulationForm(forms.ModelForm, UserKwargModelFormMixin):
    class Meta:
        model = Simulation
        exclude = ('author', )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # populate models seperating predefined and uploaded models
        predef_models = [(str(m), str(m)) for m in CellmlModel.objects.all() if m.predefined and m.is_visible_to(self.user)]
        uploaded_models = [(str(m), str(m)) for m in CellmlModel.objects.all() if not m.predefined and m.is_visible_to(self.user)]
        self.fields['model'].choices = [(None, '--- Predefined models ---')] + predef_models + [(None, '--- Uploaded models ---')] + uploaded_models

        self.fields['pacing_frequency'].widget.attrs['min'] = 0.05
        self.fields['pacing_frequency'].widget.attrs['max'] = 5.0
        self.fields['pacing_frequency'].widget.attrs['step'] = 0.01

        self.fields['maximum_pacing_time'].widget.attrs['min'] = 0.0
        self.fields['maximum_pacing_time'].widget.attrs['max'] = 120.0
        self.fields['maximum_pacing_time'].widget.attrs['step'] = 1.0

    def clean_maximum_pacing_time(self):
        maximum_pacing_time = self.cleaned_data['maximum_pacing_time']
        if maximum_pacing_time <= 0:
            raise forms.ValidationError('Maximum pacing time cannot be 0.')
        return maximum_pacing_time
