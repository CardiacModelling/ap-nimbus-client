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
