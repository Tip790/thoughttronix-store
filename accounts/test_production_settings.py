"""Production hardening: the security flags that switch on with DEBUG off."""

import importlib.util
from pathlib import Path

import environs
import pytest
from django.conf import settings
from django.core.checks import Tags, run_checks
from django.test import override_settings

FLAGS = (
    "SESSION_COOKIE_SECURE",
    "CSRF_COOKIE_SECURE",
    "SECURE_SSL_REDIRECT",
    "SECURE_HSTS_SECONDS",
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    "SECURE_HSTS_PRELOAD",
)


def load_settings(monkeypatch, **environ):
    """A fresh copy of ``config/settings.py`` read under ``environ`` only.

    A developer's own ``.env`` is ignored, so it can't leak into the
    defaults under test.
    """
    monkeypatch.setattr(environs.env, "read_env", lambda *args, **kwargs: None)
    for name in ("DEBUG", *FLAGS):
        monkeypatch.delenv(name, raising=False)
    for name, value in environ.items():
        monkeypatch.setenv(name, value)
    path = Path(settings.BASE_DIR) / "config" / "settings.py"
    spec = importlib.util.spec_from_file_location("settings_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_debug_on_sets_none_of_the_production_flags(monkeypatch):
    loaded = load_settings(monkeypatch, DEBUG="True")

    assert loaded.SESSION_COOKIE_SECURE is False
    assert loaded.CSRF_COOKIE_SECURE is False
    assert loaded.SECURE_SSL_REDIRECT is False
    assert loaded.SECURE_HSTS_SECONDS == 0
    assert loaded.SECURE_HSTS_INCLUDE_SUBDOMAINS is False
    assert loaded.SECURE_HSTS_PRELOAD is False


def test_debug_is_on_with_no_environment(monkeypatch):
    loaded = load_settings(monkeypatch)

    assert loaded.DEBUG is True
    assert loaded.SECURE_SSL_REDIRECT is False


def test_debug_off_switches_every_flag_on(monkeypatch):
    loaded = load_settings(monkeypatch, DEBUG="False")

    assert loaded.SESSION_COOKIE_SECURE is True
    assert loaded.CSRF_COOKIE_SECURE is True
    assert loaded.SECURE_SSL_REDIRECT is True
    assert loaded.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    assert loaded.SECURE_HSTS_PRELOAD is True


def test_hsts_is_short_lived_with_debug_off(monkeypatch):
    loaded = load_settings(monkeypatch, DEBUG="False")

    assert 0 < loaded.SECURE_HSTS_SECONDS <= 60 * 60


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        ("SESSION_COOKIE_SECURE", "False", False),
        ("CSRF_COOKIE_SECURE", "False", False),
        ("SECURE_SSL_REDIRECT", "False", False),
        ("SECURE_HSTS_SECONDS", "0", 0),
        ("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False", False),
        ("SECURE_HSTS_PRELOAD", "False", False),
    ],
)
def test_each_flag_can_be_turned_off_with_debug_off(monkeypatch, name, value, expected):
    loaded = load_settings(monkeypatch, DEBUG="False", **{name: value})

    assert getattr(loaded, name) == expected


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        ("SESSION_COOKIE_SECURE", "True", True),
        ("SECURE_SSL_REDIRECT", "True", True),
        ("SECURE_HSTS_SECONDS", "86400", 86400),
    ],
)
def test_flags_can_be_turned_on_with_debug_on(monkeypatch, name, value, expected):
    loaded = load_settings(monkeypatch, DEBUG="True", **{name: value})

    assert getattr(loaded, name) == expected


def test_deploy_check_passes_with_debug_off(monkeypatch):
    loaded = load_settings(monkeypatch, DEBUG="False")
    production = {name: getattr(loaded, name) for name in FLAGS}

    with override_settings(
        DEBUG=False,
        SECRET_KEY="a-real-secret-key-" + "x9Q#v2" * 10,
        **production,
    ):
        warnings = run_checks(include_deployment_checks=True, tags=[Tags.security])

    assert warnings == []
