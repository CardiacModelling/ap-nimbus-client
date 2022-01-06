import os

import django.db.models.deletion
from django.conf import settings
from django.db import models
from files.models import CellmlModel, IonCurrent
from django.core.validators import MaxValueValidator, MinValueValidator


class Simulation(models.Model):
    class IonCurrentType(models.TextChoices):
        PIC50 = 'pIC50', _('PIC50')
        IC50 = 'IC50', _('IC50')

    class IonCurrentUnits(models.TextChoices):
        logM = '-log(M)', _('-log(M)')
        M = 'M', _('M')
        µM = 'µM', _('µM')
        nM = 'nM', _('nM')

    notes = TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)
    
    model = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=CellmlModel)
    pacing_frequency = models.DecimalField(required=True, default=0.05, help_text="(in Hz) Frequency of pacing (between 0.05 and 5)", validators=[MinValueValidator(Decimal('0.05')), MaxValueValidator(Decimal('5.0')))
    maximum_pacing_time = models.DecimalField(required=True, default=5, help_text="(in mins) Maximum pacing time (between 0 and 120)", validators=[MinValueValidator(Decimal('0.0000017')), MaxValueValidator(Decimal('120')))

    ion_current_type = models.CharField(choices=IonCurrentType.choices, required=True)
    ion_units = models.CharField(choices=IonCurrentUnits.choices, required=True)
                                  
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
