from django.db import models

class CellmlModel(models.Model):
    name = models.CharField(max_length=255,
                            help_text = "The name of the model, e.g. <em>O'Hara-Rudy</em>.")
    description = models.CharField(
                      max_length=255, default='',
                      help_text = "A short description e.g. <em>human ventricular cell model (endocardial)</em>."
                  )
    version = models.CharField(max_length=255, default='', blank=True,
                               help_text = "An (optional) version, e.g. <em>CiPA-v1.0</em>.")
    year = models.IntegerField(blank=True,
                               help_text = "The year this specific model (version) was published e.g. <em>2017</em>.")
    predefined = models.BooleanField(
                     default=False,
                     help_text = "Indicates whether this is a predefined model (only available to admin users)."
                 )
    cellml_link = models.URLField(
                      max_length=200, blank=True, null=True,
                      help_text = "An (optional) link to a description of the cellml. e.g. on <em>www.cellml.org</em>."
                  )
    paper_link = models.URLField(
                     max_length=200, blank=True, null=True,
                     help_text = "An (optional) link to a paper related to the model."
                 )
    cellml_file = models.FileField(blank=False, upload_to="media",
                                   help_text = "Please upload the cellml file here.")
