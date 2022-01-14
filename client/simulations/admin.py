from django.contrib import admin

from .models import Simulation, SimulationIonCurrentParam, CompoundConcentrationPoints


admin.site.register(Simulation)
admin.site.register(SimulationIonCurrentParam)
admin.site.register(CompoundConcentrationPoints)
