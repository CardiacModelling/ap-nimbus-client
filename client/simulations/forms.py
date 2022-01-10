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
        self.fields['ion_current'].widget = forms.HiddenInput()

        self.fields['current'].widget.attrs['title'] = '> 0 for IC50.'
        self.fields['current'].widget.attrs['class'] = 'current-concentration'

        self.fields['hill_coefficient'].widget.attrs['min'] = 0.1
        self.fields['hill_coefficient'].widget.attrs['max'] = 5.0
        self.fields['hill_coefficient'].widget.attrs['step'] = 0.1
        self.fields['hill_coefficient'].widget.attrs['title'] = 'Between 0.1 and 5.'

        self.fields['saturation_level'].widget.attrs['min'] = 0.0
        self.fields['saturation_level'].widget.attrs['step'] = 1.0
        self.fields['saturation_level'].widget.attrs['title'] = 'Level of peak current relative to control at a very large compound concentration (between 0 and 1).\n- For an inhibitor this is in the range 0% (default) to <100% (compound has no effect).\n- For an activator Minimum > 100% (no effect) to Maximum 500% (as a guideline).'

        self.fields['spread_of_uncertainty'].widget.attrs['min'] = 0.0000000000000001
        self.fields['spread_of_uncertainty'].widget.attrs['max'] = 2.0
        self.fields['spread_of_uncertainty'].widget.attrs['step'] = 0.01
        self.fields['spread_of_uncertainty'].widget.attrs['title'] = 'Spread of uncertainty (between 0 and 2).\nDefaults are estimates based on a study by Elkins et all.\nIdeally all these numbers would be replaced based on the spread you observe in fitted pIC50s.'

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
        predef_models = [(m.id, str(m)) for m in CellmlModel.objects.all() if m.predefined and m.is_visible_to(self.user)]
        uploaded_models = [(m.id, str(m)) for m in CellmlModel.objects.all() if not m.predefined and m.is_visible_to(self.user)]

        self.fields['model'].choices = [(None, '--- Predefined models ---')] + predef_models + [(None, '--- Uploaded models ---')] + uploaded_models
        self.fields['ion_current_type'].choices = Simulation.IonCurrentType.choices

        self.fields['pacing_frequency'].widget.attrs['min'] = 0.05
        self.fields['pacing_frequency'].widget.attrs['max'] = 5.0
        self.fields['pacing_frequency'].widget.attrs['step'] = 0.01


        self.fields['maximum_pacing_time'].widget.attrs['min'] = 0.0
        self.fields['maximum_pacing_time'].widget.attrs['max'] = 120.0
        self.fields['maximum_pacing_time'].widget.attrs['step'] = 1.0

    def clean_title(self):
        title = self.cleaned_data['title']
        if self._meta.model.objects.filter(title=title, author=self.user).exists():
            raise forms.ValidationError('You already have a simulation with this title. The title must be unique!')
        return title

    def clean_maximum_pacing_time(self):
        maximum_pacing_time = self.cleaned_data['maximum_pacing_time']
        if maximum_pacing_time <= 0:
            raise forms.ValidationError('Maximum pacing time cannot be 0.')
        return maximum_pacing_time

    def save(self, **kwargs):
        simulation = super().save(commit=False)
        if not hasattr(simulation, 'author') or simulation.author is None:
            simulation.author = self.user
        simulation.save()
