import os

from core.models import UserCreatedModelMixin, VisibilityModelMixin
from django.db import models
from django.dispatch import receiver


class CellmlModel(UserCreatedModelMixin, VisibilityModelMixin):
    name = models.CharField(max_length=255, unique=True,
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
        max_length=200, blank=True, null=True,
        help_text="An (optional) link to a description of the cellml. e.g. on <em>www.cellml.org</em>."
    )
    paper_link = models.URLField(
        max_length=200, blank=True, null=True,
        help_text="An (optional) link to a paper related to the model."
    )
    ap_predict_model_call = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="--model call to pass to Ap Predict e.g. <em>--model 1</em> or "
                  "<em>--model shannon_wang_puglisi_weber_bers_2004</em>. This option is only available to admins and "
                  "cannot be combianed with uploading a cellml file."
    )
    cellml_file = models.FileField(null=True, blank=True, upload_to="",
                                   help_text="Please upload the cellml file here.")


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
    if not instance.pk:
        return False

    try:
        old_file = CellmlModel.objects.get(pk=instance.pk).cellml_file
    except CellmlModel.DoesNotExist:
        return False

    new_file = instance.cellml_file
    if not old_file == new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)
