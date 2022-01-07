import os

import django.db.models.deletion
from django.db.models import TextField
from django.conf import settings
from django.db import models
from files.models import CellmlModel, IonCurrent


class Simulation(models.Model):
    class IonCurrentType(models.TextChoices):
        PIC50 = 'pIC50', 'PIC50'
        IC50 = 'IC50', 'IC50'

    class IonCurrentUnits(models.TextChoices):
        negLogM = '-log(M)', '-log(M)'
        M = 'M', 'M'
        µM = 'µM', 'µM'
        nM = 'nM', 'nM'

    title = TextField(blank=True, default='', help_text="A shot title to identify this simulation by.")
    notes = TextField(blank=True, default='', help_text="A description of the simulation.")
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)

    model = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=CellmlModel)
    pacing_frequency = models.FloatField(default=0.05, help_text="(in Hz) Frequency of pacing (between 0.05 and 5)")
    maximum_pacing_time = models.FloatField(default=5, help_text="(in mins) Maximum pacing time (between 0 and 120)")

    ion_current_type = models.CharField(choices=IonCurrentType.choices, max_length=255)
    ion_units = models.CharField(choices=IonCurrentUnits.choices, max_length=255)

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

class SimulationIonCurrentParam(models.Model):
    simulation = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=Simulation)
    ion_current = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=IonCurrent)
    hill_coefficient = models.FloatField(default=1)
    saturation_level = models.FloatField(default=0)
    spread_of_uncertainty = models.FloatField(default=1)
