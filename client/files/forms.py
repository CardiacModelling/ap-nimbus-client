from django.forms import ModelForm
from .models import Model

class ModelForm(ModelForm):
    class Meta: 
        model = Model
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # predefined is only available to admin
        if not self.request.user.is_superuser:
            self.fields.pop('predefined')

# restrict upload to cellml
# edit viewitems
# list view