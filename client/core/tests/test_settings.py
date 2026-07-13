import importlib
import os
import sys
from unittest.mock import patch

import pytest


_REQUIRED_SETTINGS_ENV = {
    "DJANGO_SUPERUSER_EMAIL": "django@test.com",
    "DJANGO_SECRET_KEY": "django very secret key, honest",
    "PGDATABASE": "django",
    "PGUSER": "client",
    "PGPASSWORD": "not-so-secret django db password",
    "PGHOST": "localhost",
    "PGPORT": "5432",
    # Force LDAP off so an ambient AP_PREDICT_LDAP=1 (patch.dict uses clear=False)
    # can't enable the LDAP block and raise ImproperlyConfigured. Tests that exercise
    # the LDAP path live in test_ldap.py and set this explicitly.
    "AP_PREDICT_LDAP": "0",
}


def _import_settings(module_name, env_overrides=None):
    """Re-import a settings module under a controlled environment.

    The suite runs under config.production_settings; re-importing a settings module
    here with a scoped environment exercises it without changing the active Django
    configuration.
    """
    original_module = sys.modules.get(module_name)

    scoped_env = dict(_REQUIRED_SETTINGS_ENV)
    scoped_env.update(env_overrides or {})

    try:
        with patch.dict(os.environ, scoped_env, clear=False):
            sys.modules.pop(module_name, None)
            return importlib.import_module(module_name)
    finally:
        sys.modules.pop(module_name, None)
        if original_module is not None:
            sys.modules[module_name] = original_module


def _import_develop_settings(env_overrides=None):
    return _import_settings("config.develop_settings", env_overrides)


def test_import_is_hermetic_against_ambient_ldap_toggle():
    # An ambient AP_PREDICT_LDAP=1 must not leak into the re-import (patch.dict uses
    # clear=False); otherwise the LDAP block would enable and raise ImproperlyConfigured
    # for the missing required LDAP env, making this module non-hermetic.
    with patch.dict(os.environ, {"AP_PREDICT_LDAP": "1"}, clear=False):
        module = _import_settings("config.production_settings")
    assert module.AP_PREDICT_LDAP is False


def test_develop_settings_defaults():
    module = _import_develop_settings({"AP_PREDICT_SQLITE": "0"})

    assert module.DEBUG is True
    assert module.ALLOWED_HOSTS == ["*"]
    assert module.MEDIA_ROOT == "."
    assert module.AP_PREDICT_SQLITE is False
    # Without the SQLite opt-in, the inherited postgres backend is kept.
    assert module.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
    assert module.LOGGING["root"]["level"] == "DEBUG"
    assert module.TEMPLATES[0]["APP_DIRS"] is True


def test_develop_settings_sqlite_backend():
    module = _import_develop_settings({"AP_PREDICT_SQLITE": "1"})

    assert module.AP_PREDICT_SQLITE is True
    assert module.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
    assert module.DATABASES["default"]["NAME"].endswith("db.sqlite3")


@pytest.mark.parametrize("blank", ["", "   "])
def test_production_blank_env_falls_back_to_defaults(blank):
    # Present-but-blank vars (empty like the docker/env template, or whitespace-only)
    # must use their default rather than an empty/invalid value; int() vars must not raise.
    # ALLOWED_HOSTS is included: a blank value must not become [""] (DisallowedHost).
    module = _import_settings(
        "config.production_settings",
        {
            "ALLOWED_HOSTS": blank,
            "smtp_server": blank,
            "django_email_from_addr": blank,
            "WELCOME_SUBJECT": blank,
            "APPREDICT_LOOKUP_TABLE_MANIFEST": blank,
            "AP_PREDICT_ENDPOINT": blank,
            "AP_PREDICT_STATUS_TIMEOUT": blank,
        },
    )

    assert module.ALLOWED_HOSTS == ["*"]
    assert module.EMAIL_HOST == "localhost"
    # Falls back to DJANGO_SUPERUSER_EMAIL (from _REQUIRED_SETTINGS_ENV).
    assert module.SERVER_EMAIL == "django@test.com"
    assert module.DEFAULT_FROM_EMAIL == "django@test.com"
    assert module.WELCOME_SUBJECT == "[AP Portal] Welcome"
    assert module.APPREDICT_LOOKUP_TABLE_MANIFEST.startswith("https://")
    assert module.AP_PREDICT_ENDPOINT == "http://path_to_ap_manager"
    assert module.AP_PREDICT_STATUS_TIMEOUT == 1000


@pytest.mark.parametrize("blank", ["", "   "])
def test_production_blank_subfolder_is_treated_as_unset(blank):
    # A blank/whitespace subfolder must not become part of the URL prefix
    # (e.g. FORCE_SCRIPT_NAME "/   /"); it should be treated as unset.
    module = _import_settings("config.production_settings", {"subfolder": blank})
    assert module.subfolder is None
    assert module.FORCE_SCRIPT_NAME == ""


def test_production_subfolder_is_stripped():
    module = _import_settings("config.production_settings", {"subfolder": "  app  "})
    assert module.subfolder == "app"
    assert module.FORCE_SCRIPT_NAME == "/app/"


def test_production_allowed_hosts_parses_comma_separated():
    # A real (non-blank) value is split into a host list; surrounding spaces and
    # empty items (e.g. a trailing comma) are stripped so no host has leading
    # whitespace or is "" (which would never match and could trigger DisallowedHost).
    module = _import_settings(
        "config.production_settings", {"ALLOWED_HOSTS": "example.com, www.example.com,"}
    )
    assert module.ALLOWED_HOSTS == ["example.com", "www.example.com"]


@pytest.mark.parametrize("blank", ["", "   "])
def test_develop_blank_env_falls_back_to_defaults(blank):
    # int("") / int("  ") would raise; a blank AP_PREDICT_SQLITE must behave as "off".
    module = _import_develop_settings({"AP_PREDICT_SQLITE": blank})
    assert module.AP_PREDICT_SQLITE is False
