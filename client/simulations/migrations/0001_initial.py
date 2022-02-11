# Generated by Django 4.0.2 on 2022-02-11 20:13

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import simulations.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('files', '0002_auto_20220105_1304'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Simulation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(blank=True, choices=[('NOT_STARTED', 'Not Started'), ('INITIALISING', 'Initialising'), ('RUNNING', 'Running'), ('SUCCESS', 'Success'), ('FAILED', 'Failed')], default='NOT_STARTED', max_length=255)),
                ('title', models.CharField(help_text='A short title to identify this simulation.', max_length=255)),
                ('notes', models.TextField(blank=True, default='', help_text='Any notes related to this simulation. Please note: These will also be visible to admin users.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('pacing_frequency', models.FloatField(default=1.0, help_text='(in Hz) Frequency of pacing (between 0.05 and 5).', validators=[django.core.validators.MinValueValidator(0.05), django.core.validators.MaxValueValidator(5)])),
                ('maximum_pacing_time', models.FloatField(default=5, help_text='(in mins) Maximum pacing time (between 0 and 120).', validators=[simulations.models.StrictlyGreaterValidator(0), django.core.validators.MaxValueValidator(120)])),
                ('ion_current_type', models.CharField(choices=[('pIC50', 'pIC50'), ('IC50', 'IC50')], help_text='Ion current type.', max_length=255)),
                ('ion_units', models.CharField(choices=[('-log(M)', '-log(M)'), ('M', 'M'), ('µM', 'µM'), ('nM', 'nM')], help_text='Ion current units.', max_length=255)),
                ('pk_or_concs', models.CharField(choices=[('compound_concentration_range', 'Compound Concentration Range'), ('compound_concentration_points', 'Compound Concentration Points'), ('pharmacokinetics', 'Pharmacokinetics')], default='compound_concentration_range', max_length=255)),
                ('minimum_concentration', models.FloatField(blank=True, default=0, help_text='(in µM) at least 0.', null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('maximum_concentration', models.FloatField(blank=True, default=100, help_text='(in µM) > minimum_concentration.', null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('intermediate_point_count', models.CharField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10')], default='4', help_text='Count of plasma concentrations between the minimum and maximum (between 0 and 10).', max_length=255)),
                ('intermediate_point_log_scale', models.BooleanField(default=True, help_text='Use log scale for intermediate points.')),
                ('PK_data', models.FileField(blank=True, help_text='File format: tab-seperated values (TSV). Encoding: UTF-8\nColumn 1 : Time (hours)\nColumns 2-31 : Concentrations (µM).', upload_to='')),
                ('progress', models.CharField(blank=True, default='Initialising..', max_length=255)),
                ('ap_predict_last_update', models.DateTimeField(blank=True, null=True)),
                ('ap_predict_call_id', models.CharField(blank=True, max_length=255)),
                ('ap_predict_messages', models.CharField(blank=True, max_length=255)),
                ('q_net', models.TextField(blank=True, max_length=255)),
                ('voltage_traces', models.TextField(blank=True, max_length=255)),
                ('voltage_results', models.TextField(blank=True, max_length=255)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='files.cellmlmodel')),
            ],
            options={
                'ordering': ('-created_at', 'model'),
                'unique_together': {('title', 'author')},
            },
        ),
        migrations.CreateModel(
            name='SimulationIonCurrentParam',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current', models.FloatField(blank=True, help_text='> 0 for IC50.', null=True)),
                ('hill_coefficient', models.FloatField(blank=True, default=1, help_text='Between 0.1 and 5.', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(5)])),
                ('saturation_level', models.FloatField(blank=True, default=0, help_text='Level of peak current relative to control at a very large compound concentration (between 0 and 1).\n- For an inhibitor this is in the range 0% (default) to <100% (compound has no effect).\n- For an activator Minimum > 100% (no effect) to Maximum 500% (as a guideline).', validators=[django.core.validators.MinValueValidator(0)])),
                ('spread_of_uncertainty', models.FloatField(blank=True, help_text='Spread of uncertainty (between 0 and 2).\nDefaults are estimates based on a study by Elkins et all.\nIdeally all these numbers would be replaced based on the spread you observe in fitted pIC50s.', null=True, validators=[simulations.models.StrictlyGreaterValidator(0), django.core.validators.MaxValueValidator(2)])),
                ('ion_current', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='files.ioncurrent')),
                ('simulation', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='simulations.simulation')),
            ],
        ),
        migrations.CreateModel(
            name='CompoundConcentrationPoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('concentration', models.FloatField(help_text='(in µM) at least 0.', validators=[django.core.validators.MinValueValidator(0)])),
                ('simulation', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='simulations.simulation')),
            ],
            options={
                'ordering': ('concentration',),
            },
        ),
    ]
