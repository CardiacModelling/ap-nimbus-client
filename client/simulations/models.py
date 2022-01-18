import os

import django.db.models.deletion
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.dispatch import receiver
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext as _
from files.models import CellmlModel, IonCurrent


@deconstructible
class StrictlyGreaterValidator(MinValueValidator):
    """
    Validator expectign value to be strictly greater (not equal).
    """
    message = _('Ensure this value is greater than %(limit_value)s.')

    def compare(self, a, b):
        return a <= b


class Simulation(models.Model):
    """
    Main simulation model
    """
    class IonCurrentType(models.TextChoices):
        PIC50 = 'pIC50', 'pIC50'
        IC50 = 'IC50', 'IC50'

    class IonCurrentUnits(models.TextChoices):
        negLogM = '-log(M)', '-log(M)'
        M = 'M', 'M'
        µM = 'µM', 'µM'
        nM = 'nM', 'nM'

    class PkOptions(models.TextChoices):
        compound_concentration_range = 'compound_concentration_range', 'Compound Concentration Range'
        compound_concentration_points = 'compound_concentration_points', 'Compound Concentration Points'
        pharmacokinetics = 'pharmacokinetics', 'Pharmacokinetics'

    title = models.CharField(max_length=255, help_text="A short title to identify this simulation.")
    notes = models.TextField(blank=True, default='',
                             help_text="Any notes related to this simulation. Please note: These will also be visible "
                                       "to admin users.")
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)

    model = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=CellmlModel)
    pacing_frequency = models.FloatField(default=0.05, help_text="(in Hz) Frequency of pacing (between 0.05 and 5).",
                                         validators=[MinValueValidator(0.05), MaxValueValidator(5)])
    maximum_pacing_time = models.FloatField(default=5, help_text="(in mins) Maximum pacing time (between 0 and 120).",
                                            validators=[StrictlyGreaterValidator(0), MaxValueValidator(120)])

    ion_current_type = models.CharField(choices=IonCurrentType.choices, max_length=255, help_text="Ion current type.")
    ion_units = models.CharField(choices=IonCurrentUnits.choices, max_length=255, help_text="Ion current units.")

    pk_or_concs = models.CharField(max_length=255, choices=PkOptions.choices, default='compound_concentration_range')
    minimum_concentration = models.FloatField(blank=True, null=True, default=0, help_text="(in µM) at least 0.",
                                              validators=[MinValueValidator(0)])
    maximum_concentration = models.FloatField(blank=True, null=True, default=100,
                                              help_text="(in µM) > minimum_concentration.",
                                              validators=[MinValueValidator(0)])
    intermediate_point_count = models.CharField(
        max_length=255, choices=[(str(i), str(i)) for i in range(11)], default='4',
        help_text='Count of plasma concentrations between the minimum and maximum (between 0 and 10).'
    )
    intermediate_point_log_scale = models.BooleanField(default=True, help_text='Use log scale for intermediate points.')
    PK_data = models.FileField(blank=True, help_text="File format: tab-seperated values (TSV). Encoding: UTF-8\n"
                                                     "Column 1 : Time (hours)\nColumns 2-31 : Concentrations (µM).")

    class Meta:
        unique_together = ('title', 'author')
        ordering = ('-created_at', 'model')

    def __str__(self):
        return self.title

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
        return self.is_editable_by(user)


class SimulationIonCurrentParam(models.Model):
    """
    Ion current parameter for a given simulation
    """
    simulation = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=Simulation)
    ion_current = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=IonCurrent)
    # can't validate as restriction only if IC50 selected. Form javascript should validate
    current = models.FloatField(blank=True, null=True, help_text="> 0 for IC50.")
    hill_coefficient = models.FloatField(default=1, help_text="Between 0.1 and 5.",
                                         validators=[MinValueValidator(0), MaxValueValidator(5)])
    saturation_level = models.FloatField(default=0, validators=[MinValueValidator(0)],
                                         help_text="Level of peak current relative to control at a very large compound "
                                                   "concentration (between 0 and 1).\n- For an inhibitor this is in the"
                                                   " range 0% (default) to <100% (compound has no effect).\n- For an "
                                                   "activator Minimum > 100% (no effect) to Maximum 500% (as a "
                                                   "guideline).")
    spread_of_uncertainty = models.FloatField(blank=True, null=True, default=1,
                                              validators=[StrictlyGreaterValidator(0), MaxValueValidator(2)],
                                              help_text="Spread of uncertainty (between 0 and 2).\nDefaults are "
                                                        "estimates based on a study by Elkins et all.\nIdeally all "
                                                        "these numbers would be replaced based on the spread you "
                                                        "observe in fitted pIC50s.")

    def __str__(self):
        return str(self.ion_current) + " - " + str(self.simulation)


class CompoundConcentrationPoint(models.Model):
    """
    Concentration point for a given simulation
    """
    simulation = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=Simulation)
    concentration = models.FloatField(validators=[MinValueValidator(0), ], help_text="(in µM) at least 0.")

    def __str__(self):
        return str(self.simulation) + " - " + str(self.concentration)


@receiver(models.signals.post_delete, sender=Simulation)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `Simulation` object is deleted.
    """
    if instance.PK_data:
        if os.path.isfile(instance.PK_data.path):
            os.remove(instance.PK_data.path)
