import importlib
import os
import sys
from unittest.mock import patch

import ldap
import pytest
from config import production_settings
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django_auth_ldap.config import GroupOfNamesType, LDAPSearch


_REQUIRED_SETTINGS_ENV = {
    "DJANGO_SUPERUSER_EMAIL": "django@test.com",
    "DJANGO_SECRET_KEY": "django very secret key, honest",
    "PGDATABASE": "django",
    "PGUSER": "client",
    "PGPASSWORD": "not-so-secret django db password",
    "PGHOST": "localhost",
    "PGPORT": "5432",
}

_LDAP_OPTIONAL_KEYS = {
    "AUTH_LDAP_GROUP_SEARCH",
    "AUTH_LDAP_USER_GROUP",
    "AUTH_LDAP_ADMIN_GROUP",
    "AUTH_LDAP_SEARCH_BASE2",
    "AUTH_LDAP_SEARCH_BASE3",
    "AUTH_LDAP_SEARCH_BASE4",
    "AUTH_LDAP_SEARCH_BASE5",
}

# production_settings now requires these to be set explicitly when LDAP is enabled
# (no demo defaults), so provide them for import tests that enable LDAP.
_REQUIRED_LDAP_ENV = {
    "AUTH_LDAP_SERVER_URI": "ldap://localhost:1389",
    "AUTH_LDAP_BIND_DN": "cn=admin,dc=example,dc=com",
    "AUTH_LDAP_BIND_PASSWORD": "admin",
    "AUTH_LDAP_SEARCH_BASE": "ou=mathematicians,dc=example,dc=com",
}


def _import_settings_with_env(env_overrides):
    module_name = "config.production_settings"
    original_module = sys.modules.get(module_name)

    scoped_env = dict(_REQUIRED_SETTINGS_ENV)
    if (env_overrides.get("AP_PREDICT_LDAP") or "0") not in ("0", ""):
        scoped_env.update(_REQUIRED_LDAP_ENV)
    scoped_env.update(env_overrides)

    try:
        with patch.dict(os.environ, scoped_env, clear=False):
            for key in _LDAP_OPTIONAL_KEYS:
                if key not in scoped_env:
                    os.environ.pop(key, None)

            sys.modules.pop(module_name, None)
            return importlib.import_module(module_name)
    finally:
        sys.modules.pop(module_name, None)
        if original_module is not None:
            sys.modules[module_name] = original_module


def _build_ldap_overrides(custom_params=None):
    """Build LDAP override settings from environment and custom params."""
    custom_params = custom_params or {}

    # Get LDAP config from environment, with sensible defaults for local testing
    ldap_server_uri = os.environ.get("AUTH_LDAP_SERVER_URI", "ldap://localhost:1389")
    ldap_bind_dn = os.environ.get("AUTH_LDAP_BIND_DN", "cn=admin,dc=example,dc=com")
    ldap_bind_password = os.environ.get("AUTH_LDAP_BIND_PASSWORD", "admin")
    ldap_search_base = os.environ.get("AUTH_LDAP_SEARCH_BASE", "ou=mathematicians,dc=example,dc=com")
    ldap_search_filter = os.environ.get("AUTH_LDAP_SEARCH_FILTER", "(mail=%(user)s)")

    # Build the overrides dict from production_settings
    overrides = {
        "AP_PREDICT_LDAP": True,
        "AUTHENTICATION_BACKENDS": (
            production_settings.AUTHENTICATION_BACKENDS
            if hasattr(production_settings, "AUTHENTICATION_BACKENDS")
            else [
                "django_auth_ldap.backend.LDAPBackend",
                "django.contrib.auth.backends.ModelBackend",
            ]
        ),
        "AUTH_LDAP_SERVER_URI": ldap_server_uri,
        "AUTH_LDAP_USER_ATTR_MAP": (
            production_settings.AUTH_LDAP_USER_ATTR_MAP
            if hasattr(production_settings, "AUTH_LDAP_USER_ATTR_MAP")
            else {"full_name": "cn", "email": "mail"}
        ),
        # Without a user search the LDAPBackend cannot locate users, so the login
        # tests would fail against a real server. Settings load with LDAP disabled
        # under DJANGO_SETTINGS_MODULE, so this must be supplied explicitly here.
        "AUTH_LDAP_USER_SEARCH": LDAPSearch(ldap_search_base, ldap.SCOPE_SUBTREE, ldap_search_filter),
        "AUTH_LDAP_BIND_DN": ldap_bind_dn,
        "AUTH_LDAP_BIND_PASSWORD": ldap_bind_password,
    }

    # Apply custom parameter overrides
    # Handle AUTH_LDAP_GROUP_SEARCH: if a string is provided, convert to LDAPSearch
    if "AUTH_LDAP_GROUP_SEARCH" in custom_params:
        group_search_base = custom_params["AUTH_LDAP_GROUP_SEARCH"]
        if isinstance(group_search_base, str):
            overrides["AUTH_LDAP_GROUP_SEARCH"] = LDAPSearch(
                group_search_base, ldap.SCOPE_SUBTREE, "(objectClass=groupOfNames)"
            )
            overrides["AUTH_LDAP_GROUP_TYPE"] = GroupOfNamesType()
        else:
            overrides["AUTH_LDAP_GROUP_SEARCH"] = group_search_base

    # Handle AUTH_LDAP_USER_GROUP: map it to AUTH_LDAP_REQUIRE_GROUP
    if "AUTH_LDAP_USER_GROUP" in custom_params:
        overrides["AUTH_LDAP_REQUIRE_GROUP"] = custom_params["AUTH_LDAP_USER_GROUP"]

    # Apply remaining custom params
    for key, value in custom_params.items():
        if key not in ("AUTH_LDAP_GROUP_SEARCH", "AUTH_LDAP_USER_GROUP"):
            overrides[key] = value

    return overrides


@pytest.fixture
def ldap_settings(request):
    """Fixture that applies LDAP settings overrides."""
    custom_params = getattr(request, "param", {})
    overrides = _build_ldap_overrides(custom_params)

    with override_settings(**overrides):
        yield


@pytest.fixture
def ldap_connection(ldap_settings, settings):
    connection = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
    try:
        connection.simple_bind_s(settings.AUTH_LDAP_BIND_DN, settings.AUTH_LDAP_BIND_PASSWORD)
    except Exception as exc:
        # In CI the LDAP service is expected to be up, so a connection failure is a
        # real error rather than a reason to silently drop coverage. Only skip when
        # running locally without a server.
        if os.environ.get("CI"):
            raise
        pytest.skip(f"LDAP integration tests require a running LDAP server: {exc}")

    try:
        yield connection
    finally:
        connection.unbind_s()


def _decode_ldap_values(values):
    decoded = []
    for value in values:
        if isinstance(value, bytes):
            decoded.append(value.decode())
        else:
            decoded.append(value)
    return decoded


@pytest.mark.django_db
def test_ldap_user_login(client, ldap_connection):
    # Users log in with their email (the mail attribute), matching USERNAME_FIELD.
    assert client.login(username="ldapuser@example.com", password="ldapuserpassword")
    assert client.login(username="nogroupuser@example.com", password="nogroupuserpassword")
    assert not client.login(username="ldapuser@example.com", password="wrongpassword")
    assert not client.login(username="nosuchuser@example.com", password="ldapuserpassword")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "ldap_settings",
    [{"AUTH_LDAP_GROUP_SEARCH": "ou=mathematicians,dc=example,dc=com"}],
    indirect=True,
)
def test_ldap_group_search(ldap_connection, settings):
    assert settings.AUTH_LDAP_GROUP_SEARCH.base_dn == "ou=mathematicians,dc=example,dc=com"
    group_results = settings.AUTH_LDAP_GROUP_SEARCH.execute(ldap_connection)

    assert len(group_results) == 1
    group_dn, group_attrs = group_results[0]
    assert group_dn == "cn=statisticians,ou=mathematicians,dc=example,dc=com"
    assert "statisticians" in _decode_ldap_values(group_attrs["cn"])
    assert "uid=ldapuser,ou=mathematicians,dc=example,dc=com" in _decode_ldap_values(group_attrs["member"])


def test_ldap_admin_group_search():
    module = _import_settings_with_env(
        {
            "AP_PREDICT_LDAP": "1",
            "AUTH_LDAP_GROUP_SEARCH": "ou=mathematicians,dc=example,dc=com",
            "AUTH_LDAP_USER_GROUP": "cn=statisticians,ou=mathematicians,dc=example,dc=com",
            "AUTH_LDAP_ADMIN_GROUP": "cn=statisticians,ou=mathematicians,dc=example,dc=com",
        }
    )

    assert module.AUTH_LDAP_GROUP_SEARCH.base_dn == "ou=mathematicians,dc=example,dc=com"
    assert isinstance(module.AUTH_LDAP_GROUP_TYPE, GroupOfNamesType)
    assert module.AUTH_LDAP_REQUIRE_GROUP == "cn=statisticians,ou=mathematicians,dc=example,dc=com"
    assert module.AUTH_LDAP_USER_FLAGS_BY_GROUP == {
        "is_staff": "cn=statisticians,ou=mathematicians,dc=example,dc=com",
        "is_superuser": "cn=statisticians,ou=mathematicians,dc=example,dc=com",
    }


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
def test_ldap_user_group_login(client, ldap_connection, settings):
    assert settings.AUTH_LDAP_REQUIRE_GROUP == "cn=statisticians,ou=mathematicians,dc=example,dc=com"
    assert client.login(username="ldapuser@example.com", password="ldapuserpassword")
    assert not client.login(username="nogroupuser@example.com", password="nogroupuserpassword")


def test_production_settings_ldap_disabled_path():
    module = _import_settings_with_env({"AP_PREDICT_LDAP": "0"})

    assert module.AP_PREDICT_LDAP is False
    assert not hasattr(module, "AUTH_LDAP_USER_SEARCH")


def test_ldap_search_base_branch():
    module = _import_settings_with_env(
        {
            "AP_PREDICT_LDAP": "1",
            "AUTH_LDAP_SEARCH_BASE2": "ou=alternate,dc=example,dc=com",
        }
    )

    search_bases = [search.base_dn for search in module.AUTH_LDAP_USER_SEARCH.searches]
    assert "ou=mathematicians,dc=example,dc=com" in search_bases
    assert "ou=alternate,dc=example,dc=com" in search_bases


@pytest.mark.parametrize("blank", ["", "   "])
def test_ldap_blank_optional_env_is_treated_as_unset(blank):
    # Present-but-blank vars (empty like a docker-compose `AUTH_LDAP_GROUP_SEARCH=`
    # line, or whitespace-only) must be treated as unset, not configured.
    module = _import_settings_with_env(
        {
            "AP_PREDICT_LDAP": "1",
            "AUTH_LDAP_GROUP_SEARCH": blank,
            "AUTH_LDAP_USER_GROUP": blank,
            "AUTH_LDAP_ADMIN_GROUP": blank,
            "AUTH_LDAP_SEARCH_BASE2": blank,
        }
    )

    assert not hasattr(module, "AUTH_LDAP_GROUP_SEARCH")
    assert not hasattr(module, "AUTH_LDAP_REQUIRE_GROUP")
    assert not hasattr(module, "AUTH_LDAP_USER_FLAGS_BY_GROUP")
    # The blank extra base must not add an (invalid) empty-base search.
    search_bases = [search.base_dn for search in module.AUTH_LDAP_USER_SEARCH.searches]
    assert search_bases == ["ou=mathematicians,dc=example,dc=com"]


@pytest.mark.parametrize(
    "missing", ["AUTH_LDAP_SERVER_URI", "AUTH_LDAP_BIND_DN", "AUTH_LDAP_BIND_PASSWORD", "AUTH_LDAP_SEARCH_BASE"]
)
def test_ldap_enabled_without_required_env_fails_fast(missing):
    # Enabling LDAP without an explicit value for a required setting must raise at
    # import (startup) rather than falling back to a demo default.
    with pytest.raises(ImproperlyConfigured):
        _import_settings_with_env({"AP_PREDICT_LDAP": "1", missing: ""})


def test_ldap_required_env_is_stripped_when_assigned():
    # Whitespace fat-fingered into an env file passes validation (which strips before
    # checking), so the assigned structural values must be stripped too. The bind
    # password is deliberately preserved verbatim, as edge whitespace may be significant.
    module = _import_settings_with_env(
        {
            "AP_PREDICT_LDAP": "1",
            "AUTH_LDAP_SERVER_URI": "  ldap://localhost:1389  ",
            "AUTH_LDAP_BIND_DN": "  cn=admin,dc=example,dc=com  ",
            "AUTH_LDAP_BIND_PASSWORD": "  admin  ",
            "AUTH_LDAP_SEARCH_BASE": "  ou=mathematicians,dc=example,dc=com  ",
        }
    )

    assert module.AUTH_LDAP_SERVER_URI == "ldap://localhost:1389"
    assert module.AUTH_LDAP_BIND_DN == "cn=admin,dc=example,dc=com"
    assert module.AUTH_LDAP_BIND_PASSWORD == "  admin  "
    search_bases = [search.base_dn for search in module.AUTH_LDAP_USER_SEARCH.searches]
    assert search_bases == ["ou=mathematicians,dc=example,dc=com"]
