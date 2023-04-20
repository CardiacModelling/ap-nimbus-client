import pytest
from core.templatetags.ap_nimubs import (
    can_edit,
    contact_mailto,
    contact_text,
    hosting_info,
)
from django.conf import settings


@pytest.mark.django_db
def test_can_edit(user, other_user, admin_user, o_hara_model):
    for usr in (user, other_user, admin_user):
        o_hara_model.save()
        context = {'user': usr}
        assert can_edit(context, o_hara_model) == \
            (o_hara_model.author == usr or (o_hara_model.predefined and usr.is_superuser))


@pytest.mark.django_db
def test_hosting_info():
    return hosting_info() == settings.HOSTING_INFO


@pytest.mark.django_db
def test_contact_mailto():
    return contact_mailto() == settings.CONTACT_MAILTO


@pytest.mark.django_db
def test_contact_text():
    return contact_text() == settings.CONTACT_TEXT
