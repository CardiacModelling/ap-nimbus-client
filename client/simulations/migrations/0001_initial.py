# Generated by Django 3.2.10 on 2022-01-06 17:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('files', '0002_auto_20220105_1304'),
    ]

    operations = [
        migrations.CreateModel(
            name='Simulation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.TextField(blank=True, default='', help_text="A shot title to identify this simulation by.")),
                ('notes', models.TextField(blank=True, default='', help_text="A description of the simulation.")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('pacing_frequency', models.FloatField(default=0.05, help_text='(in Hz) Frequency of pacing (between 0.05 and 5)')),
                ('maximum_pacing_time', models.FloatField(default=5, help_text='(in mins) Maximum pacing time (between 0 and 120)')),
                ('ion_current_type', models.CharField(choices=[('pIC50', 'PIC50'), ('IC50', 'IC50')], max_length=255)),
                ('ion_units', models.CharField(choices=[('-log(M)', '-log(M)'), ('M', 'M'), ('µM', 'µM'), ('nM', 'nM')], max_length=255)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='files.cellmlmodel')),
            ],
        ),
        migrations.CreateModel(
            name='SimulationIonCurrentParam',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hill_coefficient', models.FloatField(default=1)),
                ('saturation_level', models.FloatField(default=0)),
                ('spread_of_uncertainty', models.FloatField(default=1)),
                ('ion_current', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='files.ioncurrent')),
                ('simulation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='simulations.simulation')),
            ],
        ),
    ]
