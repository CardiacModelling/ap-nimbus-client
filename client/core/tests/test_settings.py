import importlib
import os
import sys
from unittest.mock import patch


_REQUIRED_SETTINGS_ENV = {
    "DJANGO_SUPERUSER_EMAIL": "django@test.com",
    "DJANGO_SECRET_KEY": "django very secret key, honest",
    "PGDATABASE": "django",
    "PGUSER": "client",
    "PGPASSWORD": "not-so-secret django db password",
    "PGHOST": "localhost",
    "PGPORT": "5432",
}


def _import_develop_settings(env_overrides=None):
    """Re-import config.develop_settings under a controlled environment.

    The test suite runs under config.production_settings, so develop_settings is
    otherwise never imported. Importing it here (mirroring the production_settings
    approach in test_ldap) exercises the module without changing the active
    Django configuration.
    """
    module_name = "config.develop_settings"
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
