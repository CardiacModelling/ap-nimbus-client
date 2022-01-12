import django.db.models.deletion
from django.conf import settings
from django.db import models
from files.models import CellmlModel, IonCurrent


class Simulation(models.Model):
    class IonCurrentType(models.TextChoices):
        PIC50 = 'pIC50', 'pIC50'
        IC50 = 'IC50', 'IC50'

    class IonCurrentUnits(models.TextChoices):
        negLogM = '-log(M)', '-log(M)'
        M = 'M', 'M'
        µM = 'µM', 'µM'
        nM = 'nM', 'nM'

    title = models.CharField(max_length=255, help_text="A short title to identify this simulation.")
    notes = models.TextField(blank=True, default='',
                             help_text="Any notes related to this simulation. Please note: These will also be visible "
                                       "to admin users.")
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)

    model = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=CellmlModel)
    pacing_frequency = models.FloatField(default=0.05, help_text="(in Hz) Frequency of pacing (between 0.05 and 5).")
    maximum_pacing_time = models.FloatField(default=5, help_text="(in mins) Maximum pacing time (between 0 and 120).")

    ion_current_type = models.CharField(choices=IonCurrentType.choices, max_length=255, help_text="Ion current type.")
    ion_units = models.CharField(choices=IonCurrentUnits.choices, max_length=255, help_text="Ion current units.")

    class Meta:
        unique_together = ('title', 'author')

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
        return self.predefined or user.is_superuser or user == self.author


class SimulationIonCurrentParam(models.Model):
    simulation = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=Simulation)
    ion_current = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=IonCurrent)
    current = models.FloatField(blank=True, null=True, help_text="> 0 for IC50.")
    hill_coefficient = models.FloatField(default=1, help_text="Between 0.1 and 5.")
    saturation_level = models.FloatField(default=0,
                                         help_text="Level of peak current relative to control at a very large compound "
                                                   "concentration (between 0 and 1).\n- For an inhibitor this is in the"
                                                   " range 0% (default) to <100% (compound has no effect).\n- For an "
                                                   "activator Minimum > 100% (no effect) to Maximum 500% (as a "
                                                   "guideline).")
    spread_of_uncertainty = models.FloatField(blank=True, null=True, default=1,
                                              help_text="Spread of uncertainty (between 0 and 2).\nDefaults are "
                                                        "estimates based on a study by Elkins et all.\nIdeally all "
                                                        "these numbers would be replaced based on the spread you "
                                                        "observe in fitted pIC50s.")

    def __str__(self):
        return str(self.ion_current) + " - " + str(self.simulation)
