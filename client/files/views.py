from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from .forms import ModelForm
from .models import Model


class ModelView(LoginRequiredMixin):
    model = Model
    form_class = RegistrationForm
    template_name = 'files/model.html'
    success_url = reverse_lazy('home')
