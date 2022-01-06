from braces.forms import UserKwargModelFormMixin
from cellmlmanip import load_model
from django import forms

from files.models import CellmlModel, IonCurrent
from .models import Simulation, SimulationIonCurrentParam



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
        self.fields['model'].choices = predef_models + [(None, '--- Uploaded models ---')] + uploaded_models
        # set starting model choice
        if predef_models:
            self.fields['model'].initial = predef_models[1][0]

        # remove empty choices for ion corrent params
        self.fields['ion_current_type'].choices = Simulation.IonCurrentType.choices
        self.fields['ion_units'].choices = Simulation.IonCurrentUnits.choices
        for current in IonCurrent.objects.all():
            self.fields[str(current)] = forms.FloatField()
            self.fields[str(current) + '_hill_coefficient'] = forms.FloatField()
            self.fields[str(current) + '_saturation_level'] = forms.FloatField()
            self.fields[str(current) + '_spread_of_uncertainty'] = forms.FloatField()

