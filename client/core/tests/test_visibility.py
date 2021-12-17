import pytest
from core.visibility import (  # visibility_check,
    CHOICES,
    HELP_TEXT,
    Visibility,
    get_help_text,
    get_visibility_choices,
)


@pytest.mark.django_db
def test_visibility_choices(user, admin_user):
    choices = ((Visibility.PUBLIC, 'Public'),
               (Visibility.MODERATED, 'Moderated'),
               (Visibility.PRIVATE, 'Private'))
    assert CHOICES == choices
    assert tuple(get_visibility_choices(admin_user)) == choices
    assert tuple(get_visibility_choices(user)) == (choices[0], choices[2])


@pytest.mark.django_db
def test_get_help_text(user, admin_user):
    help_text = (
        'Moderated = public and checked by a moderator<br/>'
        'Public = anyone can view<br/>'
        'Private = only you can view'
    )
    assert HELP_TEXT == help_text
    assert get_help_text(admin_user) == help_text
    assert get_help_text(user) == 'Public = anyone can view<br/>Private = only you can view'
