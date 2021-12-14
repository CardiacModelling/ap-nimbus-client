from datetime import datetime

import magic
from core import visibility
from django import forms
from django.core.exceptions import ValidationError

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

    def clean(self):
        cleaned_data = super().clean()
        if (cleaned_data['ap_predict_model_call'] is None) == (cleaned_data['cellml_file'] is None):
            if 'ap_predict_model_call' not in self.fields:
                raise ValidationError("A Cellml file is required")
            else:
                raise ValidationError("Either a cellml file or an Ap Predict call is required (bot not both)")

        if cleaned_data.get('cellml_file', None):
            mime_type = str(magic.from_file(cleaned_data['cellml_file'].temporary_file_path(), mime=True))
            if mime_type not in ['text/xml', 'application/xml']:
                raise ValidationError('Unsupported file type, expecting a cellml file.')

        return cleaned_data

    def save(self, **kwargs):
        model = super().save(commit=False)
        if not hasattr(model, 'author') or model.author is None:
            model.author = self.user
        model.save()
        return model
