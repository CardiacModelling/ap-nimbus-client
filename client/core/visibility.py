from django.contrib.auth.mixins import AccessMixin
from django.http import Http404


class Visibility:
    PRIVATE = 'private'
    PUBLIC = 'public'
    MODERATED = 'moderated'


HELP_TEXT = (
    'Moderated = public and checked by a moderator<br/>'
    'Public = anyone can view<br/>'
    'Private = only you can view'
)

CHOICES = (
    (Visibility.PUBLIC, 'Public'),
    (Visibility.MODERATED, 'Moderated'),
    (Visibility.PRIVATE, 'Private'),
)


def get_visibility_choices(user):
    return (c for c in CHOICES if user.is_superuser or not c[0] == Visibility.MODERATED)


def get_help_text(user):
    if user.is_superuser:
        return HELP_TEXT
    else:
        return HELP_TEXT.replace('Moderated = public and checked by a moderator<br/>', '')


def visibility_check(visibility, allowed_users, user):
    """
    Visibility check

    :param visibility: `Visibility` value
    :param allowed_users: Users that have special privileges in this scenario
    :param: user: user to test against

    :returns: True if the user has permission to view, False otherwise
    """
    if visibility in [Visibility.PUBLIC, Visibility.MODERATED]:
        # Public and moderated are visible to everybody
        return True

    elif user.is_authenticated:
        # Logged in user can view all except other people's private stuff
        # unless given special permissions to do so
        return (
            user in allowed_users or
            visibility != Visibility.PRIVATE
        )

    return False


class VisibilityMixin(AccessMixin):
    """
    View mixin implementing visiblity restrictions

    Public and moderated objects can be seen by all.
    Private objects can be seen only by their owner.

    If an object is not visible to a logged in user, we generate a 404
    If an object is not visible to an anonymous visitor, redirect to login page
    """
    def dispatch(self, request, *args, **kwargs):
        # We want to treat "not visible" the same way as "does not exist" -
        # so defer any exception handling until later
        try:
            obj = self.get_object()
        except Http404:
            obj = None

        allow_access = False

        if obj:
            if visibility_check(self.get_visibility(),
                                self.get_viewers(),
                                self.request.user):
                allow_access = True
            else:
                auth_header = self.request.META.get('HTTP_AUTHORIZATION')
                if auth_header and auth_header.startswith('Token'):
                    token = auth_header[5:].strip()
                    allow_access = self.check_access_token(token)

        if allow_access:
            return super().dispatch(request, *args, **kwargs)

        elif self.request.user.is_authenticated:
            # For logged in user, raise a 404
            raise Http404
        else:
            # For anonymous user, redirect to login page
            return self.handle_no_permission()
