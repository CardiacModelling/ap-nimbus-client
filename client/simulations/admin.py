from django.contrib import admin

from .models import CompoundConcentrationPoint, Simulation, SimulationIonCurrentParam


admin.site.register(Simulation)
admin.site.register(SimulationIonCurrentParam)
admin.site.register(CompoundConcentrationPoint)
