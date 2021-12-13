import urllib.parse

from django.conf import settings
from django.db import models
from django.urls import reverse

from . import visibility
from .visibility import HELP_TEXT as VIS_HELP_TEXT
from accounts.models import User


class VisibilityModelMixin(models.Model):
    """
    Model mixin for giving objects different levels of visibility
    """
    visibility = models.CharField(
        max_length=16,
        choices=visibility.CHOICES,
        help_text=visibility.HELP_TEXT,
        default=visibility.CHOICES[0],
    )

    class Meta:
        abstract = True


class UserCreatedModelMixin(models.Model):
    """
    Model mixin for user-created objects
    """
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    VISIBILITY_HELP = VIS_HELP_TEXT

    def is_editable_by(self, user):
        """
        Is the entity editable by the given user?

        :param user: User object
        :return: True if deletable, False otherwise
        """
        return user.is_superuser or user == self.author

    @property
    def viewers(self):
        """
        Users who have permission to view this object

        - i.e. the author and anybody listed as a collaborator

        This overrides the 'private' visibility for the object. A 'public'
        object is visible to all anyway.
        """
        return set(User.objects.filter(is_superuser=True)) | {self.author}

    class Meta:
        abstract = True
