import pytest

from core.visibility import (
    Visibility,
    visibility_check,
)


@pytest.mark.django_db
def test_visibility_check(user, other_user, anon_user, admin_user):
    assert visibility_check(Visibility.PUBLIC, [user], user)
    assert visibility_check(Visibility.PRIVATE, [user], user)

    assert visibility_check(Visibility.PUBLIC, [], other_user)
    assert not visibility_check(Visibility.PRIVATE, [], other_user)

    assert visibility_check(Visibility.PUBLIC, [user], anon_user)
    assert not visibility_check(Visibility.PRIVATE, [user], anon_user)
    assert visibility_check(Visibility.PRIVATE, [user], admin_user)
