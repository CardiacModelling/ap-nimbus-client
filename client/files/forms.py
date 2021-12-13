from django import forms
from core import visibility
from .models import CellmlModel
from datetime import datetime

class CellmlModelForm(forms.ModelForm):
    visibility = forms.ChoiceField(
        choices=visibility.CHOICES,
        help_text=visibility.HELP_TEXT,
    )

    year = forms.ChoiceField(
        choices= [(y, y) for y in range(datetime.now().year +1, 1949, -1)],
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

    def save(self, **kwargs):
        entity = super().save(commit=False)
        entity.author = self.user
        entity.save()
        return entity
