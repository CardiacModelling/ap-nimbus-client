from datetime import datetime

import magic
from braces.forms import UserKwargModelFormMixin
from cellmlmanip import load_model
from django import forms
from django.core.files.uploadedfile import TemporaryUploadedFile, UploadedFile

from .models import CellmlModel, IonCurrent


OXMETA = 'https://chaste.comlab.ox.ac.uk/cellml/ns/oxford-metadata#'


class CellmlModelForm(forms.ModelForm, UserKwargModelFormMixin):
    class Meta:
        model = CellmlModel
        exclude = ('author', )
        widgets = {'cellml_file': forms.ClearableFileInput(attrs={'accept': '.cellml'}),
                   'year': forms.widgets.Select(choices=[(y, y) for y in range(datetime.now().year + 1, 1949, - 1)])}

    def __init__(self, *args, **kwargs):
        self.current_title = None  # current title
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields['year'].initial = datetime.now().year
        for _, field in self.fields.items():
            field.widget.attrs['title'] = field.help_text.replace('<em>', '').replace('</em>', '')

        if not self.user.is_superuser:
            self.fields.pop('predefined')
            self.fields.pop('ap_predict_model_call')
            self.fields.pop('ion_currents')

    def clean_name(self):
        name = self.cleaned_data['name']
        exists = CellmlModel.objects.filter(name=name, author=self.user)
        if self.instance:
            exists = exists.exclude(pk=self.instance.pk)
        if exists:
            raise forms.ValidationError('You already have a CellML model with this name, the name must be unique!')
        return name

    def clean_ap_predict_model_call(self):
        model_call = self.cleaned_data.get('ap_predict_model_call', None)
        if model_call and model_call.lower().strip().startswith('--model'):
            raise forms.ValidationError("Ap predict model call should not include the --model flag")

        return self.cleaned_data['ap_predict_model_call']

    def clean_cellml_file(self):
        cellml_file = self.cleaned_data.get('cellml_file', None)
        model_call = self.cleaned_data.get('ap_predict_model_call', None)

        if cellml_file is False:  # treat clearing file the same as no entry for file
            cellml_file = None

        if (model_call is None) == (cellml_file is None):  # Need either a file or model call
            raise forms.ValidationError("Either a cellml file or an Ap Predict call is required (bot not both)")

        # check mime type of any uploaded file (should be XML)
        if cellml_file and isinstance(cellml_file, UploadedFile):
            mime_type = str(magic.from_buffer(cellml_file.file.read(), mime=True))
            if mime_type not in ['text/xml', 'application/xml']:
                raise forms.ValidationError('Unsupported file type, expecting a cellml file.')

        if cellml_file and isinstance(cellml_file, TemporaryUploadedFile):
            # parse file and look for ion current metadata (can only read files, not from memory)
            try:
                self.cellmlmanip_model = load_model(cellml_file.temporary_file_path())
            except Exception as e:
                raise forms.ValidationError('Could not process cellml model: \n    ' + str(e))
        return self.cleaned_data['cellml_file']

    def save(self, **kwargs):
        model = super().save(commit=False)
        if not hasattr(model, 'author') or model.author is None:
            model.author = self.user
        model.save()

        # If a cellml file was uploaded and parse, check it for metadata tags
        if hasattr(self, 'cellmlmanip_model'):
            model.ion_currents.clear()
            for current in IonCurrent.objects.all():
                for metadata_tag in [tag.strip() for tag in current.metadata_tags.split(',')]:
                    try:
                        self.cellmlmanip_model.get_variable_by_ontology_term((OXMETA, metadata_tag))
                        model.ion_currents.add(current)
                    except KeyError:
                        pass  # model does not have current)

        model.save()
        return model
