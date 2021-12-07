from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.views.generic.edit import DeleteView, FormView, UpdateView
from django.urls import reverse_lazy

from .forms import MyAccountForm, RegistrationForm
from .models import User


class RegistrationView(FormView):
    form_class = RegistrationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('home')

    class Meta:
        fields = ('email', 'full_name', 'institution')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        user = form.save()
        login(
            self.request,
            user,
            backend='django.contrib.auth.backends.ModelBackend',
        )
        return super().form_valid(form)


class MyAccountView(LoginRequiredMixin, UpdateView):
    form_class = MyAccountForm
    template_name = 'registration/myaccount.html'
    success_url = reverse_lazy('accounts:myaccount')


class UserDeleteView(UserPassesTestMixin, DeleteView):
    """
       Delete a user
       """
    template_name = 'registration/account_confirm_delete.html'
    model = User
    success_url = reverse_lazy('home')

    def test_func(self):
        """A user can only delete their own account."""
        return self.get_object() == self.request.user
