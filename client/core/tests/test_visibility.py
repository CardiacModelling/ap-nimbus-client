import pytest
from core.visibility import (
    CHOICES,
    HELP_TEXT,
    Visibility,
    get_help_text,
    get_visibility_choices,
    visibility_check,
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


@pytest.mark.django_db
def test_visibility_check(user, other_user, anonymous_user):
    assert visibility_check(Visibility.MODERATED, [user], user)
    assert visibility_check(Visibility.PUBLIC, [user], user)
    assert visibility_check(Visibility.PRIVATE, [user], user)

    assert visibility_check(Visibility.MODERATED, [], other_user)
    assert visibility_check(Visibility.PUBLIC, [], other_user)
    assert not visibility_check(Visibility.PRIVATE, [], other_user)

    assert visibility_check(Visibility.MODERATED, [], other_user)
    assert visibility_check(Visibility.PUBLIC, [], other_user)
    assert not visibility_check(Visibility.PRIVATE, [], other_user)

    assert visibility_check(Visibility.MODERATED, [], anonymous_user)
    assert visibility_check(Visibility.PUBLIC, [], anonymous_user)
    assert not visibility_check(Visibility.PRIVATE, [], anonymous_user)

