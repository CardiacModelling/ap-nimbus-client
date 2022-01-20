import csv

import magic
from braces.forms import UserKwargModelFormMixin
from django import forms
from django.core.files.uploadedfile import TemporaryUploadedFile, UploadedFile
from django.forms import inlineformset_factory
from files.models import CellmlModel

from .models import CompoundConcentrationPoint, Simulation, SimulationIonCurrentParam


class BaseSaveFormSet(forms.BaseFormSet):
    """
    Set of forms with a save method to save all sub forms.
    """
    def save(self, simulation=None, **kwargs):
        return [form.save(simulation=simulation, **kwargs) for form in self.forms]


class IonCurrentForm(forms.ModelForm):
    """
    Form for an Ion current parameter.
    """
    class Meta:
        model = SimulationIonCurrentParam
        exclude = ('simulation', )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields['default_spread_of_uncertainty'] = forms.CharField(widget=forms.HiddenInput())

        self.fields['current'].widget.attrs = {'class': 'current-concentration'}
        self.fields['hill_coefficient'].widget.attrs = {'min': 0.1, 'max': 5.0, 'step': 0.1}
        self.fields['hill_coefficient'].required = False

        self.fields['saturation_level'].widget.attrs = {'min': 0.0, 'step': 1.0}
        self.fields['saturation_level'].required = False

        self.fields['spread_of_uncertainty'].widget.attrs = {'min': 0.0000000000001, 'max': 2.0, 'step': 0.01,
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


#  Set of forms for Ion current parameters.
IonCurrentFormSet = inlineformset_factory(
    parent_model=Simulation,
    model=SimulationIonCurrentParam,
    form=IonCurrentForm,
    formset=BaseSaveFormSet,
    exclude=('simulation', ),
    can_delete=False,
    can_order=False,
    extra=0,
    min_num=0,
)


# Set of forms for concentration points.
class CompoundConcentrationPointForm(forms.ModelForm):
    """
    Form for a concentration point.
    """
    class Meta:
        model = CompoundConcentrationPoint
        exclude = ('simulation', ),

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields['concentration'].required = False
        self.fields['concentration'].widget.attrs = {'class': 'compound-concentration', 'required': False,
                                                     'min': 0}
        for _, field in self.fields.items():
            field.widget.attrs['title'] = field.help_text

    def save(self, simulation=None, **kwargs):
        # concentration not set, don't try to save
        if not self.cleaned_data.get('concentration', None):
            return None
        concentration = super().save(commit=False)
        concentration.simulation = simulation
        assert concentration.concentration
        concentration.save()
        return concentration


CompoundConcentrationPointFormSet = inlineformset_factory(
    parent_model=Simulation,
    model=CompoundConcentrationPoint,
    form=CompoundConcentrationPointForm,
    formset=BaseSaveFormSet,
    exclude=('simulation', ),
    can_delete=False,
    can_order=False,
    extra=0,
    min_num=5,
    max_num=30,
)


class SimulationForm(forms.ModelForm, UserKwargModelFormMixin):
    """
    Form for creating new simulations.
    """
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

        self.fields['maximum_pacing_time'].widget.attrs = {'min': 0.0000000000001, 'max': 120.0, 'step': 1.0,
                                                           'required': 'required'}

        self.fields['pk_or_concs'].widget = forms.RadioSelect(attrs={'class': 'pk_or_concs'},
                                                              choices=self.fields['pk_or_concs'].choices)
        self.fields['minimum_concentration'].widget.attrs = {'min': 0}
        self.fields['maximum_concentration'].widget.attrs = {'min': 0.0000000000001}
        self.fields['PK_data'].widget.attrs = {'accept': ('.txt,.tsv')}

        for _, field in self.fields.items():
            field.widget.attrs['title'] = field.help_text

    def clean_title(self):
        title = self.cleaned_data['title']
        if self._meta.model.objects.filter(title=title, author=self.user).exists():
            raise forms.ValidationError('You already have a simulation with this title. The title must be unique!')
        return title

    def clean_PK_data(self):
        PK_data = self.cleaned_data['PK_data']

        # check mime type of any uploaded file
        if isinstance(PK_data, UploadedFile):
            mime_type = str(magic.from_buffer(PK_data.file.read(), mime=True))
            if mime_type not in ['text/plain', 'text/tsv']:
                raise forms.ValidationError(
                    'Invalid TSV file. Unsupported file type, expecting a (UTF-8 text-based) TSV file.'
                )

        if isinstance(PK_data, TemporaryUploadedFile):
            with open(PK_data.temporary_file_path()) as file:
                tsv_file = tuple(csv.reader(file, delimiter="\t"))
                # validate TSV format
                previous_time = -1
                for line in tsv_file:
                    if len(line) < 2:
                        raise forms.ValidationError('Invalid TSV file. Expecting a TSV file with at least 2 columns.')

                    current_time = float(line[0])
                    if current_time <= previous_time:
                        raise forms.ValidationError('Invalid TSV file. Time in column 1 should be strictly increasing.')
                    previous_time = current_time

                    for i, column in enumerate(line):
                        try:
                            if float(column) < 0:
                                raise forms.ValidationError('Invalid TSV file. Got a negetive value in column %s.' % i)
                        except ValueError:
                            raise forms.ValidationError(
                                'Invalid TSV file. Expecting number values only. Got `%s.`' % column
                            )

        return PK_data

    def save(self, **kwargs):
        simulation = super().save(commit=False)
        if not hasattr(simulation, 'author') or simulation.author is None:
            simulation.author = self.user
        simulation.save()
        return simulation


class SimulationEditForm(forms.ModelForm, UserKwargModelFormMixin):
    """
    Form for editing simulations.
    We can only edit title / description not other parameters.
    For other parameters, a new simulation would be needed.
    """
    class Meta:
        model = Simulation
        fields = ('title', 'notes')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
