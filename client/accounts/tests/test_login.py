from unittest.mock import patch

import ldap
import pytest
from accounts.models import User
from django.contrib.auth import authenticate
from django.test import override_settings
from django_auth_ldap.config import LDAPSearch
from fakeldap import MockLDAP


@pytest.fixture
def valid_user():
    return User.objects.create_user(
        email="test@example.com",
        full_name="Test User",
        institution="UCL",
        password="password",
    )


@pytest.mark.django_db
def test_login_with_email(client, valid_user):
    assert client.login(username=valid_user.email, password="password")


@pytest.mark.django_db
@override_settings(
    AP_PREDICT_LDAP=True,
    AUTHENTICATION_BACKENDS=[
        "django_auth_ldap.backend.LDAPBackend",
        "django.contrib.auth.backends.ModelBackend",
    ],
    AUTH_LDAP_SERVER_URI="ldap://mockldap",
    AUTH_LDAP_BIND_DN="cn=read-only-admin,dc=example,dc=com",
    AUTH_LDAP_BIND_PASSWORD="password",
    AUTH_LDAP_USER_SEARCH=LDAPSearch(
        "ou=mathematicians,dc=example,dc=com",
        ldap.SCOPE_ONELEVEL,
        "(mail=%(user)s)",
    ),
    AUTH_LDAP_USER_ATTR_MAP={"full_name": "cn"},
)
def test_mock_ldap_login():
    directory = {
        "cn=read-only-admin,dc=example,dc=com": {
            "userPassword": "password",
        },
        "mail=ldap-user@example.com,ou=mathematicians,dc=example,dc=com": {
            "mail": ["ldap-user@example.com"],
            "cn": ["LDAP Mock User"],
            "userPassword": "password",
        },
    }
    mock_ldap = MockLDAP(directory)

    with patch("django_auth_ldap.backend.ldap.initialize", return_value=mock_ldap):
        user = authenticate(username="ldap-user@example.com", password="password")

    assert user is not None
    assert user.email == "ldap-user@example.com"
    assert user.full_name == "LDAP Mock User"
    assert User.objects.filter(email="ldap-user@example.com").exists()
