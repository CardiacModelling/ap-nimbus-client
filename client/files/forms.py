from datetime import datetime

import magic
from core import visibility
from django import forms

from .models import CellmlModel


class CellmlModelForm(forms.ModelForm):
    visibility = forms.ChoiceField(
        choices=visibility.CHOICES,
        help_text=visibility.HELP_TEXT,
    )

    year = forms.ChoiceField(
        choices=[(y, y) for y in range(datetime.now().year + 1, 1949, - 1)],
        initial=datetime.now().year
    )

    class Meta:
        model = CellmlModel
        exclude = ('author', )
        widgets = {'cellml_file': forms.FileInput(attrs={'accept': '.cellml'})}

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields['visibility'].choices = visibility.get_visibility_choices(self.user)
        self.fields['visibility'].help_text = visibility.get_help_text(self.user)
        if not self.user.is_superuser:
            self.fields.pop('ap_predict_model_call')

    def clean_ap_predict_model_call(self):
        if self.cleaned_data['ap_predict_model_call'].lower().strip().startswith('--model'):
            raise forms.ValidationError("Ap predict model call should not include the --model flag")

        return self.cleaned_data['ap_predict_model_call']

    def clean_cellml_file(self):
        if 'ap_predict_model_call' in self.cleaned_data and \
                (self.cleaned_data['ap_predict_model_call'] is None) == (self.cleaned_data['cellml_file'] is None):
            raise forms.ValidationError("Either a cellml file or an Ap Predict call is required (bot not both)")
        if self.cleaned_data.get('cellml_file', None):
            mime_type = str(magic.from_file(self.cleaned_data['cellml_file'].temporary_file_path(), mime=True))
            if mime_type not in ['text/xml', 'application/xml']:
                raise forms.ValidationError('Unsupported file type, expecting a cellml file.')
        return self.cleaned_data['cellml_file']

    def save(self, **kwargs):
        model = super().save(commit=False)
        if not hasattr(model, 'author') or model.author is None:
            model.author = self.user
        model.save()
        return model
