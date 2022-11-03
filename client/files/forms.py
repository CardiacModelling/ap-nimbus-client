from datetime import datetime

import magic
from braces.forms import UserKwargModelFormMixin
from cellmlmanip import load_model
from django import forms
from django.core.files.uploadedfile import TemporaryUploadedFile, UploadedFile

from .models import AppredictLookupTableManifest, CellmlModel, IonCurrent


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
            self.fields.pop('model_name_tag')
            self.fields.pop('predefined')
            self.fields.pop('ap_predict_model_call')
            self.fields.pop('ion_currents')

    def clean(self):
        cleaned_data = super().clean()
        if hasattr(self, 'cellmlmanip_model'):
            cleaned_data['model_name_tag'] = self.cellmlmanip_model.name

        lut_manifest = AppredictLookupTableManifest.get_manifest()
        if not self.user.is_superuser and cleaned_data['model_name_tag'] in lut_manifest:
            raise forms.ValidationError('You have uploaded a CellML model with name tag: '
                                        f'{cleaned_data["model_name_tag"]} this tag is reserved for lookup table '
                                        'pruposes and models with this name can only be uploaded by admins.')

        models_with_name_tag = CellmlModel.objects.filter(model_name_tag=cleaned_data['model_name_tag'],
                                                          author=self.user)
        predef_models_with_name_tag = CellmlModel.objects.filter(model_name_tag=cleaned_data['model_name_tag'],
                                                                 predefined=True)

        if self.instance and self.instance.pk is not None:
            models_with_name_tag = models_with_name_tag.exclude(pk=self.instance.pk)
            predef_models_with_name_tag = predef_models_with_name_tag.exclude(pk=self.instance.pk)
        if models_with_name_tag.union(predef_models_with_name_tag):
            raise forms.ValidationError(f'A CellML model with the model name tag {cleaned_data["model_name_tag"]} '
                                        'exsists, the model name tag must be unique!')
        return cleaned_data

    def clean_name(self):
        name = self.cleaned_data['name']
        models_with_name = CellmlModel.objects.filter(name=name, author=self.user)
        predef_models_with_name = CellmlModel.objects.filter(name=name, predefined=True)

        if self.instance and self.instance.pk is not None:
            models_with_name = models_with_name.exclude(pk=self.instance.pk)
            predef_models_with_name = predef_models_with_name.exclude(pk=self.instance.pk)
        if models_with_name.union(predef_models_with_name):
            raise forms.ValidationError('A CellML model with this name esists, the name must be unique!')

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

        if not self.user.is_superuser and cellml_file is None:
            raise forms.ValidationError("A cellml file is required!")

        if (model_call is None) == (cellml_file is None):  # Need either a file or model call
            raise forms.ValidationError("Either a cellml file or an Ap Predict call is required!")

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
