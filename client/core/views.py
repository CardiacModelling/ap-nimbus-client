import os

from braces.views import UserFormKwargsMixin
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import FileResponse
from django.views.generic.base import RedirectView
from files.models import CellmlModel
from simulations.models import Simulation


class MediaView(LoginRequiredMixin, UserPassesTestMixin, UserFormKwargsMixin, RedirectView):
    """
    Serve files only if user has access
    (i.e. they are linked to a predefined CellmlModel or Simulation or CellmlModel they own).
    """
    def test_func(self):
        self.file_name = self.kwargs['file_name']
        my_cellml_files = CellmlModel.objects.filter(cellml_file=self.file_name, author=self.request.user)
        public_cellml_files = CellmlModel.objects.filter(cellml_file=self.file_name, predefined=True)
        my_sim = Simulation.objects.filter(PK_data=self.file_name, author=self.request.user)
        return my_cellml_files.union(public_cellml_files).exists() or my_sim.exists()

    def get(self, request, *args, **kwargs):
        return FileResponse(open(os.path.join(settings.MEDIA_ROOT, self.file_name), 'rb'),
                            as_attachment=True, filename=self.file_name)

