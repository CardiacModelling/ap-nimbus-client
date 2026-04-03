import importlib
import sys

import fakeldap
import ldap
import pytest
from django.test import override_settings


@pytest.fixture
def ldap_settings(request, monkeypatch):
    module_name = "config.production_settings"
    original_module = sys.modules.get(module_name)
    ldap_env = getattr(request, "param", {})

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

    monkeypatch.setenv("AP_PREDICT_LDAP", "1")
    for key, value in ldap_env.items():
        monkeypatch.setenv(key, value)

    sys.modules.pop(module_name, None)

    try:
        production = importlib.import_module(module_name)
        ldap_overrides = {key: getattr(production, key) for key in ldap_keys if hasattr(production, key)}

        with override_settings(**ldap_overrides):
            yield
    finally:
        sys.modules.pop(module_name, None)
        if original_module is not None:
            sys.modules[module_name] = original_module


@pytest.fixture
def mock_ldap(ldap_settings, mocker):
    # Set up a mock LDAP directory
    user_dn = "uid=ldapuser,ou=mathematicians,dc=example,dc=com"
    nogroupuser_dn = "uid=nogroupuser,ou=mathematicians,dc=example,dc=com"
    group_dn = "cn=statisticians,ou=mathematicians,dc=example,dc=com"
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
        nogroupuser_dn: {
            "uid": ["nogroupuser"],
            "mail": ["nogroupuser@example.com"],
            "cn": ["Nogroup User"],
            "sn": ["User"],
            "givenName": ["Nogroup"],
            "userPassword": ["nogroupuserpassword"],
        },
        group_dn: {
            "cn": ["statisticians"],
            "member": [user_dn],
            "objectClass": ["groupOfNames"],
        },
    }
    _mock_ldap = fakeldap.MockLDAP(directory)

    # Set up synchronous search to return entries based on the directory
    _mock_ldap.set_return_value(
        api_name="search_s",
        arguments=("ou=mathematicians,dc=example,dc=com", ldap.SCOPE_SUBTREE, "(uid=ldapuser)", None, 0),
        value=[(user_dn, directory[user_dn])],
    )

    _mock_ldap.set_return_value(
        api_name="search_s",
        arguments=("ou=mathematicians,dc=example,dc=com", ldap.SCOPE_SUBTREE, "(uid=nogroupuser)", None, 0),
        value=[(nogroupuser_dn, directory[nogroupuser_dn])],
    )

    _mock_ldap.set_return_value(
        api_name="search_s",
        arguments=("ou=mathematicians,dc=example,dc=com", ldap.SCOPE_SUBTREE, "(uid=nosuchuser)", None, 0),
        value=[],
    )

    _mock_ldap.set_return_value(
        api_name="search_s",
        arguments=("ou=mathematicians,dc=example,dc=com", ldap.SCOPE_SUBTREE, "(objectClass=groupOfNames)", None, 0),
        value=[(group_dn, directory[group_dn])],
    )

    _mock_ldap.set_return_value(
        api_name="search_s",
        arguments=(
            "ou=mathematicians,dc=example,dc=com",
            ldap.SCOPE_SUBTREE,
            "(&(objectClass=groupOfNames)(member=uid=ldapuser,ou=mathematicians,dc=example,dc=com))",
            None,
            0,
        ),
        value=[(group_dn, directory[group_dn])],
    )

    _mock_ldap.set_return_value(
        api_name="search_s",
        arguments=(
            "ou=mathematicians,dc=example,dc=com",
            ldap.SCOPE_SUBTREE,
            "(&(objectClass=groupOfNames)(member=uid=nogroupuser,ou=mathematicians,dc=example,dc=com))",
            None,
            0,
        ),
        value=[],
    )

    _mock_ldap.set_return_value(
        api_name="compare_s",
        arguments=(group_dn, "member", user_dn.encode()),
        value=1,
    )

    _mock_ldap.set_return_value(
        api_name="compare_s",
        arguments=(group_dn, "member", nogroupuser_dn.encode()),
        value=0,
    )

    # Set up asynchronous search to return the same entries
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
def test_ldap_user_login(client, mock_ldap):
    assert client.login(username="ldapuser", password="ldapuserpassword")
    assert client.login(username="nogroupuser", password="nogroupuserpassword")
    assert not client.login(username="ldapuser", password="wrongpassword")
    assert not client.login(username="nosuchuser", password="ldapuserpassword")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "ldap_settings",
    [{"AUTH_LDAP_GROUP_SEARCH": "ou=mathematicians,dc=example,dc=com"}],
    indirect=True,
)
def test_ldap_group_search(mock_ldap, settings):
    assert settings.AUTH_LDAP_GROUP_SEARCH.base_dn == "ou=mathematicians,dc=example,dc=com"
    group_results = settings.AUTH_LDAP_GROUP_SEARCH.execute(mock_ldap)
    assert group_results == [
        (
            "cn=statisticians,ou=mathematicians,dc=example,dc=com",
            {
                "cn": ["statisticians"],
                "member": ["uid=ldapuser,ou=mathematicians,dc=example,dc=com"],
                "objectClass": ["groupOfNames"],
            },
        )
    ]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "ldap_settings",
    [
        {
            "AUTH_LDAP_GROUP_SEARCH": "ou=mathematicians,dc=example,dc=com",
            "AUTH_LDAP_USER_GROUP": "cn=statisticians,ou=mathematicians,dc=example,dc=com",
        }
    ],
    indirect=True,
)
def test_ldap_user_group_login(client, mock_ldap, settings):
    assert settings.AUTH_LDAP_REQUIRE_GROUP == "cn=statisticians,ou=mathematicians,dc=example,dc=com"
    assert client.login(username="ldapuser", password="ldapuserpassword")
    assert not client.login(username="nogroupuser", password="nogroupuserpassword")
