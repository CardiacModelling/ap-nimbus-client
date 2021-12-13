import magic
from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

from core.models import UserCreatedModelMixin, VisibilityModelMixin



def validate_is_xml(file):
    if str(magic.from_file(file.path, mime=True)) not in ['text/xml', 'application/xml']:
        raise ValidationError('Unsupported file type, expecting a cellml file.')


class CellmlModel(UserCreatedModelMixin, VisibilityModelMixin):
    name = models.CharField(max_length=255, unique=True,
                            help_text = "The name of the model, e.g. <em>O'Hara-Rudy</em>.")
    description = models.CharField(
                      max_length=255, default='',
                      help_text = "A short description e.g. <em>human ventricular cell model (endocardial)</em>."
                  )
    version = models.CharField(max_length=255, default='', blank=True,
                               help_text = "An (optional) version, e.g. <em>CiPA-v1.0</em>.")
    year = models.IntegerField(blank=True,
                               help_text = "The year this specific model (version) was published e.g. <em>2017</em>.")
    cellml_link = models.URLField(
                      max_length=200, blank=True, null=True,
                      help_text = "An (optional) link to a description of the cellml. e.g. on <em>www.cellml.org</em>."
                  )
    paper_link = models.URLField(
                     max_length=200, blank=True, null=True,
                     help_text = "An (optional) link to a paper related to the model."
                 )
    cellml_file = models.FileField(blank=False, upload_to="", unique=True,
                                   help_text = "Please upload the cellml file here.",
                                   validators=[FileExtensionValidator(allowed_extensions=['cellml']), validate_is_xml]
                 )
