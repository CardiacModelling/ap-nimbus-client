import importlib
import os

import fakeldap
import ldap
import pytest
from accounts.models import User
from django.test import override_settings


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


@pytest.fixture
def ldap_settings():

    ldap_keys = [
        "AP_PREDICT_LDAP",
        "AUTHENTICATION_BACKENDS",
        "AUTH_LDAP_SERVER_URI",
        "AUTH_LDAP_USER_ATTR_MAP",
        "AUTH_LDAP_GROUP_SEARCH",
        "AUTH_LDAP_GROUP_TYPE",
        "AUTH_LDAP_REQUIRE_GROUP",
        "AUTH_LDAP_USER_FLAGS_BY_GROUP",
        "AUTH_LDAP_BIND_DN",
        "AUTH_LDAP_BIND_PASSWORD",
        "AUTH_LDAP_USER_SEARCH",
    ]

    os.environ["AP_PREDICT_LDAP"] = "1"
    production = importlib.import_module("config.production_settings")
    importlib.reload(production)
    ldap_overrides = {key: getattr(production, key) for key in ldap_keys if hasattr(production, key)}

    with override_settings(**ldap_overrides):
        yield

    os.environ.pop("AP_PREDICT_LDAP", None)


@pytest.fixture
def mock_ldap(ldap_settings, mocker):
    # Set up a mock LDAP directory with a test user
    user_dn = "uid=ldapuser,ou=mathematicians,dc=example,dc=com"
    directory = {
        "cn=read-only-admin,dc=example,dc=com": {
            "userPassword": ["password"],
            "cn": ["read-only-admin"],
        },
        user_dn: {
            "uid": ["ldapuser"],
            "mail": ["ldapuser@example.com"],
            "cn": ["Ldap User"],
            "sn": ["User"],
            "givenName": ["Ldap"],
            "userPassword": ["ldapuserpassword"],
        },
    }
    _mock_ldap = fakeldap.MockLDAP(directory)

    # Set up synchronous search to return the user entry
    _mock_ldap.set_return_value(
        api_name="search_s",
        arguments=("ou=mathematicians,dc=example,dc=com", ldap.SCOPE_SUBTREE, "(uid=ldapuser)", None, 0),
        value=[(user_dn, directory[user_dn])],
    )

    _mock_ldap.set_return_value(
        api_name="search_s",
        arguments=("ou=mathematicians,dc=example,dc=com", ldap.SCOPE_SUBTREE, "(uid=nosuchuser)", None, 0),
        value=[],
    )

    # Set up asynchronous search to return the same user entry
    async_results = {}

    def _search(base, scope, filterstr, attrlist=None):
        msgid = 1
        async_results[msgid] = _mock_ldap.search_s(base, scope, filterstr, attrlist)
        return msgid

    def _result(msgid, all=1, timeout=None):
        return (ldap.RES_SEARCH_RESULT, async_results.get(msgid, []))

    _mock_ldap.search = _search
    _mock_ldap.result = _result

    # Patch ldap.initialize to return our MockLDAP instead of a real LDAPObject
    mocker.patch("django_auth_ldap.backend.ldap.initialize", return_value=_mock_ldap)
    yield _mock_ldap


@pytest.mark.django_db
def test_ldap_login(client, mock_ldap):
    assert client.login(username="ldapuser", password="ldapuserpassword")
    assert not client.login(username="ldapuser", password="wrongpassword")
    assert not client.login(username="nosuchuser", password="ldapuserpassword")
