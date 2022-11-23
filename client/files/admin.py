from django.contrib import admin

from .models import AppredictLookupTableManifest, CellmlModel, IonCurrent


class AppredictLookupTableManifestAdmin(admin.ModelAdmin):
    readonly_fields = ('date_modified',)


admin.site.register(CellmlModel)
admin.site.register(IonCurrent)
admin.site.register(AppredictLookupTableManifest, AppredictLookupTableManifestAdmin)
