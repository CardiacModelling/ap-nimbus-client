import pytest
from core.visibility import CHOICES
from files.templatetags.files import can_edit


@pytest.mark.django_db
def test_can_edit(user, other_user, admin_user, o_hara_model):
    for c, _ in CHOICES:
        for usr in (user, other_user, admin_user):
            o_hara_model.visibility = c
            o_hara_model.save()
            context = {'user': usr}
            assert can_edit(context, o_hara_model) == o_hara_model.is_editable_by(usr)

