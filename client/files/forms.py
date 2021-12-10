from django.forms import ModelForm
from .models import CellmlModel

class CellmlModelForm(ModelForm):
    class Meta: 
        model = CellmlModel
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # predefined is only available to admin
        if not self.user.is_superuser:
            self.fields.pop('predefined')

