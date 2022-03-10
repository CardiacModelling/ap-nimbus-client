import os

import django.db.models.deletion
from django.conf import settings
from django.db import models
from django.dispatch import receiver


class IonCurrent(models.Model):
    name = models.CharField(max_length=255, unique=True,
                            help_text="A (unique) short name for the kurrent e.g. <em>IKr</em>.")
    alternative_name = models.CharField(max_length=255, blank=True, help_text="Alternative name to display alongside "
                                                                              "the name, e.g. <em>herg</em> for the "
                                                                              "name <em>IKr</em> which would be "
                                                                              "displayed as <em>IKr (herg)</em>.")
    metadata_tags = models.CharField(max_length=255,
                                     help_text="A set of metadata tags (comma seperated) in the cellml that confirms "
                                               "the presence of the current e.g. "
                                               "<em>membrane_fast_sodium_current_conductance, "
                                               "membane_fast_sodium_current_conductance_scaling_factor</em>.")
    channel_protein = models.CharField(max_length=255, blank=True)
    gene = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    default_hill_coefficient = models.FloatField(default=1,
                                                 help_text="Default hill coefficient (between 0.1 and 5).")
    default_saturation_level = models.FloatField(default=0, help_text="The (default) level of peak current "
                                                                      "relative to control at a very large "
                                                                      "compound concentration. For an inhibitor "
                                                                      "this is in the range 0% (default) to <100%"
                                                                      " (compound has no effect).<br /> For an "
                                                                      "activator Minimum > 100% (no effect) to "
                                                                      "Maximum 500% (as a guideline).")
    default_spread_of_uncertainty = models.FloatField(default=1, help_text="Default guiding value for the ion "
                                                                           "current (between 0 and 2).")
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)

    def __str__(self):
        if self.alternative_name:
            return self.name + (' (' + self.alternative_name + ')')
        else:
            return self.name


class CellmlModel(models.Model):
    predefined = models.BooleanField(
        default=False,
        help_text="Show this model as a predefined model to all users. (This option is only available to admins)."
    )
    name = models.CharField(max_length=255,
                            help_text="The name of the model, e.g. <em>O'Hara-Rudy</em>.")
    description = models.CharField(
        max_length=255, default='',
        help_text="A short description e.g. <em>human ventricular cell model (endocardial)</em>."
    )
    version = models.CharField(max_length=255, default='', blank=True,
                               help_text="An (optional) version, e.g. <em>CiPA-v1.0</em>.")
    year = models.PositiveIntegerField(
        blank=True,
        help_text="The year this specific model (version) was published e.g. <em>2017</em>."
    )
    cellml_link = models.URLField(
        max_length=255, blank=True, null=True,
        help_text="An (optional) link to a description of the cellml. e.g. on <em>www.cellml.org</em>."
    )
    paper_link = models.URLField(
        max_length=255, blank=True, null=True,
        help_text="An (optional) link to a paper related to the model."
    )
    ap_predict_model_call = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="call to pass to Ap Predict with --model parameter e.g. <em>1</em> or <em> "
                  "shannon_wang_puglisi_weber_bers_2004</em>. This option is only available to admins and cannot be "
                  "combianed with uploading a cellml file."
    )
    cellml_file = models.FileField(blank=True, upload_to="",
                                   help_text="Please upload the cellml file here. Please note: the cellml file is "
                                             "expected to be annotated.")
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)
    ion_currents = models.ManyToManyField(IonCurrent, help_text="Ion currents used. This selection is ignored when a"
                                                                " cellml file is uploaded. To edit the selection for"
                                                                " modules using a cellml file, see the admin "
                                                                "interface.", blank=True)

    class Meta:
        unique_together = ('name', 'author')

    def __str__(self):
        return self.name + (" " + self.version if self.version else '') + " (" + str(self.year) + ")"


@receiver(models.signals.post_delete, sender=CellmlModel)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `CellmlModel` object is deleted.
    """
    if instance.cellml_file:
        if os.path.isfile(instance.cellml_file.path):
            os.remove(instance.cellml_file.path)


@receiver(models.signals.pre_save, sender=CellmlModel)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """
    Deletes old file from filesystem
    when corresponding `CellmlModel` object is updated
    with new file.
    """
    if instance.pk:
        old_file = CellmlModel.objects.get(pk=instance.pk).cellml_file
        if old_file and (not instance.cellml_file or old_file.path != instance.cellml_file.path):
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)

