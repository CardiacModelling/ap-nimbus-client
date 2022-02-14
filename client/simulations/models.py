import os
import math

import django.db.models.deletion
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.dispatch import receiver
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext as _
from files.models import CellmlModel, IonCurrent
from django.utils import timezone
import requests


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
    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED"
        INITIALISING = "INITIALISING"
        RUNNING = "RUNNING"
        SUCCESS = "SUCCESS"
        FAILED = "FAILED"

    class IonCurrentType(models.TextChoices):
        PIC50 = 'pIC50', 'pIC50'
        IC50 = 'IC50', 'IC50'

    class IonCurrentUnits(models.TextChoices):
        negLogM = '-log(M)', '-log(M)'
        M = 'M', 'M'
        µM = 'µM', 'µM'
        nM = 'nM', 'nM'

    def conversion(choice):
        if choice == Simulation.IonCurrentUnits.M:
            return lambda c: - math.log10(c)
        elif choice == Simulation.IonCurrentUnits.µM:
            return lambda c: - math.log10(1e-6 * c)
        elif choice == Simulation.IonCurrentUnits.nM:
            return lambda c: - math.log10(1e-9 * c)
        else:
            return lambda c: c

    class PkOptions(models.TextChoices):
        compound_concentration_range = 'compound_concentration_range', 'Compound Concentration Range'
        compound_concentration_points = 'compound_concentration_points', 'Compound Concentration Points'
        pharmacokinetics = 'pharmacokinetics', 'Pharmacokinetics'

    status = models.CharField(choices=Status.choices, max_length=255, blank=True, default=Status.NOT_STARTED)
    title = models.CharField(max_length=255, help_text="A short title to identify this simulation.")
    notes = models.TextField(blank=True, default='',
                             help_text="Any notes related to this simulation. Please note: These will also be visible "
                                       "to admin users.")
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)

    model = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=CellmlModel)
    pacing_frequency = models.FloatField(default=1.0, help_text="(in Hz) Frequency of pacing (between 0.05 and 5).",
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
    progress = models.CharField(max_length=255, blank=True, default='Initialising..')
    ap_predict_last_update = models.DateTimeField(blank=True, default=timezone.now)
    ap_predict_call_id = models.CharField(max_length=255, blank=True)
    ap_predict_messages = models.CharField(max_length=255, blank=True)
    q_net = models.TextField(max_length=255, blank=True)
    voltage_traces = models.TextField(max_length=255, blank=True)
    voltage_results = models.TextField(max_length=255, blank=True)

    class Meta:
        unique_together = ('title', 'author')
        ordering = ('-created_at', 'model')

    def __str__(self):
        return self.title

    def start_simulation(self):
        """
        Makes the request to start the simulation if a simulation.
        """
        #todo: pk_data, cellml_file
        call_data = {'pacingFrequency': self.pacing_frequency,
                     'pacingMaxTime': self.maximum_pacing_time}

        if self.pk_or_concs == Simulation.PkOptions.pharmacokinetics:
            pass #pkdata
        elif self.pk_or_concs == Simulation.PkOptions.compound_concentration_points:
            call_data['plasmaPoints'] = [c.concentration for c in CompoundConcentrationPoint.objects.filter(simulation=self)]
        else: # sim.pk_or_concs == Simulation.PkOptions.compound_concentration_range:
            call_data['plasmaMaximum'] = self.maximum_concentration
            call_data['plasmaMinimum'] = self.minimum_concentration
            call_data['plasmaIntermediatePointCount'] = self.intermediate_point_count
            call_data['plasmaIntermediatePointLogScale'] = self.intermediate_point_log_scale

        if self.model.ap_predict_model_call:
            call_data['modelId'] = self.model.ap_predict_model_call
        else:
            call_data['modelId'] = self.model.cellml_file.url

        for current_param in SimulationIonCurrentParam.objects.filter(simulation=self):
            call_data[current_param.ion_current.name] = {
                'associatedData': [{'pIC50': Simulation.conversion(self.ion_units)(current_param.current),
                                    'hill': current_param.hill_coefficient,
                                    'saturation': current_param.saturation_level}]
            }
            if current_param.spread_of_uncertainty:
                call_data[current_param.ion_current.name]['spreads'] = \
                    {'c50Spread': current_param.spread_of_uncertainty}

        call_response = {}
        try:
            response = requests.post(settings.AP_PREDICT_ENDPOINT, timeout=settings.AP_PREDICT_TIMEOUT, json=call_data)
            response.raise_for_status()  # Raise exception if request response doesn't return successful status
            call_response = response.json()
            self.ap_predict_call_id = call_response['success']['id']
            self.status = Simulation.Status.INITIALISING
            self.ap_predict_last_update = timezone.now()
        except requests.exceptions.RequestException as http_err:
            self.status = Simulation.Status.FAILED
            self.progress = 'Failed!'
            self.ap_predict_messages = 'Call to start sim failed: %s' % type(http_err)
        except KeyError:
            self.status = Simulation.Status.FAILED
            self.progress = 'Failed!'
            self.ap_predict_messages = call_response
        finally:
            self.save()

    def re_start_simulation(self):
        """
        First try to get fresh progress  going. If that doesn't work, try to stop the simulation, then restart.
        """
        # restart if it was a succesful run, or there is no new progress we missed
        progress, status = self.progress, self.status
        self.update_progress()
        if self.progress == progress and self.status == status:
            # try to stop simulation
            try:
                response = requests.get(settings.AP_PREDICT_ENDPOINT + '/api/collection/%s/STOP' % self.ap_predict_call_id,
                                        timeout=settings.AP_PREDICT_TIMEOUT)
            except requests.exceptions.RequestException as http_err:
                self.ap_predict_messages = 'Call to stop sim failed: %s' % type(http_err)
            # restart simulation
            self.status=Simulation.Status.NOT_STARTED
            self.progress = 'Initialising..'
            self.save()
            self.start_simulation()

    def update_progress(self):
        """
        Updates the current progress of a running simulation.
        """
        # can't update without call_id
        # no need updating if we have result
        if not self.ap_predict_call_id or self.status == Simulation.Status.SUCCESS:
            return self
        else:
            try:
                response = requests.get(settings.AP_PREDICT_ENDPOINT + '/api/collection/%s/progress_status' % self.ap_predict_call_id,
                                        timeout=settings.AP_PREDICT_TIMEOUT)
                response.raise_for_status()  # Raise exception if request response doesn't return successful status
                call_response = response.json()
                last_update = self.ap_predict_last_update
                if 'success' in call_response:
                    progress_text = next((p for p in reversed(call_response['success']) if p), '')
                    self.status = Simulation.Status.RUNNING
                    if progress_text == '..done!':
                        self.progress = progress_text
                        store_results(self)
                        last_update = self.ap_predict_last_update = timezone.now()
                    elif self.progress != progress_text:
                        self.progress = progress_text
                        last_update = self.ap_predict_last_update = timezone.now()
                delta = timezone.now() - last_update
                if delta.seconds > settings.AP_PREDICT_STATUS_TIMEOUT:
                    self.status = Simulation.Status.FAILED
                    self.progress = 'Failed!'
                    self.ap_predict_messages = 'status has not changed in %s seconds' % settings.AP_PREDICT_STATUS_TIMEOUT

            except requests.exceptions.RequestException as http_err:
                self.status = Simulation.Status.FAILED
                self.progress = 'Failed!'
                self.ap_predict_messages = 'Call to get progress failed: %s' % type(http_err)
            finally:
                self.save()
                return self

    def store_results(self):
        """
        Stores simulation results.
        """
        for command in ('q_net', 'voltage_traces', 'voltage_results'):
            try:
                response = requests.get(settings.AP_PREDICT_ENDPOINT + '/api/collection/%s/%s' % (self.ap_predict_call_id, command),
                                        timeout=settings.AP_PREDICT_TIMEOUT)
                response.raise_for_status()  # Raise exception if request response doesn't return successful status
                call_response = response.json()
                setattr(self, command, call_response['success'])
            except requests.exceptions.RequestException as http_err: #also add timeout
                self.status = Simulation.Status.FAILED
                self.progress = 'Failed!'
                self.ap_predict_messages = 'Call to get results failed: %s' % type(http_err)
            except KeyError:
                pass  # these types of results are not available
        self.save()
        if self.voltage_traces and self.voltage_results:
            self.status = Simulation.Status.SUCCESS
            self.save()



class SimulationIonCurrentParam(models.Model):
    """
    Ion current parameter for a given simulation
    """
    simulation = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=Simulation, blank=True)
    ion_current = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=IonCurrent)
    # can't validate as restriction only if IC50 selected. Form javascript should validate
    current = models.FloatField(blank=True, null=True, help_text="> 0 for IC50.")
    hill_coefficient = models.FloatField(default=1, help_text="Between 0.1 and 5.", blank=True,
                                         validators=[MinValueValidator(0), MaxValueValidator(5)])
    saturation_level = models.FloatField(default=0, validators=[MinValueValidator(0)], blank=True,
                                         help_text="Level of peak current relative to control at a very large compound "
                                                   "concentration (between 0 and 1).\n- For an inhibitor this is in the"
                                                   " range 0% (default) to <100% (compound has no effect).\n- For an "
                                                   "activator Minimum > 100% (no effect) to Maximum 500% (as a "
                                                   "guideline).")
    spread_of_uncertainty = models.FloatField(blank=True, null=True,
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
    simulation = models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=Simulation, blank=True)
    concentration = models.FloatField(validators=[MinValueValidator(0), ], help_text="(in µM) at least 0.")

    class Meta:
        ordering = ('concentration', )

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

