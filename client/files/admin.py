from django.contrib import admin

from .models import CellmlModel, IonCurrent


admin.site.register(CellmlModel)
admin.site.register(IonCurrent)
