import os

import django.db.models.deletion
from django.conf import settings
from django.db import models
from django.dispatch import receiver


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
        help_text="call to pass to Ap Predict with --model parameter e.g. <em> 1</em> or <em> "
                  "shannon_wang_puglisi_weber_bers_2004</em>. This option is only available to admins and cannot be "
                  "combianed with uploading a cellml file."
    )
    cellml_file = models.FileField(blank=True, upload_to="",
                                   help_text="Please upload the cellml file here.")
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)
  
class Meta:
    unique_together = ('name', 'author')

    def __str__(self):
        return self.name + (" " + self.version if self.version else '') + " (" + str(self.year) + ")"

    def is_editable_by(self, user):
        """
        Is the entity editable by the given user?
        :param user: User object
        :return: True if deletable, False otherwise
        """
        return user.is_superuser or user == self.author

    def is_visible_to(self, user):
        """
        Can the user view this model?
        """
        return self.predefined or user.is_superuser or user == self.author


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

