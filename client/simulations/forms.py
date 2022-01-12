from braces.forms import UserKwargModelFormMixin
from django import forms
from django.forms import inlineformset_factory
from files.models import CellmlModel

from .models import Simulation, SimulationIonCurrentParam


class BaseSimulationFormSet(forms.BaseFormSet):
    def save(self, simulation=None, **kwargs):
        return [form.save(simulation=simulation, **kwargs) for form in self.forms]


class IonCurrentForm(forms.ModelForm, UserKwargModelFormMixin):
    class Meta:
        model = SimulationIonCurrentParam
        exclude = ('author', 'simulation')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields['default_spread_of_uncertainty'] = forms.CharField(widget=forms.HiddenInput())

        self.fields['current'].widget.attrs = {'title': '> 0 for IC50.', 'disabled': 'disabled',
                                               'class': 'current-concentration'}
        self.fields['hill_coefficient'].widget.attrs = {'min': 0.1, 'max': 5.0, 'step': 0.1}
        self.fields['hill_coefficient'].required = False

        self.fields['saturation_level'].widget.attrs = {'min': 0.0, 'step': 1.0}
        self.fields['saturation_level'].required = False

        self.fields['spread_of_uncertainty'].widget.attrs = {'min': 0.0000000000000001, 'max': 2.0, 'step': 0.01,
                                                             'class': 'spread_of_uncertainty'}

        for _, field in self.fields.items():
            field.widget.attrs['title'] = field.help_text

    def save(self, simulation=None, **kwargs):
        # current not set, don't try to save
        if not self.cleaned_data.get('current', None):
            return None
        param = super().save(commit=False)
        param.simulation = simulation
        param.save()
        return param


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
        predef_models = [(m.id, str(m)) for m in CellmlModel.objects.all()
                         if m.predefined and m.is_visible_to(self.user)]
        uploaded_models = [(m.id, str(m)) for m in CellmlModel.objects.all()
                           if not m.predefined and m.is_visible_to(self.user)]
        self.fields['model'].choices = [(None, '--- Predefined models ---')] + predef_models + \
            [(None, '--- Uploaded models ---')] + uploaded_models
        self.fields['ion_current_type'].choices = Simulation.IonCurrentType.choices

        self.fields['pacing_frequency'].widget.attrs = {'min': 0.05, 'max': 5.0, 'step': 0.01, 'required': 'required'}

        self.fields['maximum_pacing_time'].widget.attrs = {'min': 0.0000000000000001, 'max': 120.0, 'step': 1.0,
                                                           'required': 'required'}
        for _, field in self.fields.items():
            field.widget.attrs['title'] = field.help_text

    def clean_title(self):
        title = self.cleaned_data['title']
        if self._meta.model.objects.filter(title=title, author=self.user).exists():
            raise forms.ValidationError('You already have a simulation with this title. The title must be unique!')
        return title

    def save(self, **kwargs):
        simulation = super().save(commit=False)
        if not hasattr(simulation, 'author') or simulation.author is None:
            simulation.author = self.user
        simulation.save()
        return simulation
