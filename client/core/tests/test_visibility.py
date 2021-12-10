import pytest

from core.visibility import (
    Visibility,
    get_joint_visibility,
    visibility_check,
)


@pytest.mark.django_db
def test_visibility_check(user, other_user, anon_user, admin_user):
    assert visibility_check('public', [user], user)
    assert visibility_check('private', [user], user)

    assert visibility_check('public', [], other_user)
    assert not visibility_check('private', [], other_user)

    assert visibility_check('public', [user], anon_user)
    assert not visibility_check('private', [user], anon_user)
    assert visibility_check('private', [user], admin_user)
