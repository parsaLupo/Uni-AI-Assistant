"""Release/local-demo environment validation (Phase 16).

The validator backs the container entrypoint; these tests pin every refusal so
a local release cannot silently boot with the dev secret, DEBUG on, weak
database credentials, or implicit cookie/HTTPS flags.
"""

from __future__ import annotations

from config.release_check import validate

SECRET = "s" * 48
DB_PASSWORD = "d" * 24


def valid_local_demo() -> dict[str, str]:
    return {
        "DEPLOYMENT_MODE": "local-demo",
        "DJANGO_DEBUG": "false",
        "DJANGO_SECRET_KEY": SECRET,
        "ALLOWED_HOSTS": "localhost,127.0.0.1",
        "CORS_ALLOWED_ORIGINS": "",
        "DATABASE_URL": f"postgresql://usa_user:{DB_PASSWORD}@db:5432/usa_db",
        "DOCUMENT_STORAGE_ROOT": "/app/media",
        "COOKIE_SECURE": "false",
        "SECURE_SSL_REDIRECT": "false",
        "SECURE_HSTS_SECONDS": "0",
        "CELERY_TASK_ALWAYS_EAGER": "false",
        "CELERY_BROKER_URL": "redis://redis:6379/0",
        "AI_PROVIDER": "mock",
        "DEMO_MODE": "true",
        "DEMO_PASSWORD": "Demo-Local-Passw0rd",
    }


def test_valid_local_demo_environment_passes():
    assert validate(valid_local_demo()) == []


def test_non_release_mode_is_not_validated():
    assert validate({"DEPLOYMENT_MODE": "dev"}) == []


def test_debug_must_be_false():
    env = valid_local_demo()
    env["DJANGO_DEBUG"] = "true"
    assert any("DJANGO_DEBUG" in error for error in validate(env))


def test_secret_must_be_strong_and_not_the_dev_value():
    env = valid_local_demo()
    env["DJANGO_SECRET_KEY"] = "dev-only-insecure-key-do-not-use-in-production"
    assert any("DJANGO_SECRET_KEY" in error for error in validate(env))
    env["DJANGO_SECRET_KEY"] = "short"
    assert any("DJANGO_SECRET_KEY" in error for error in validate(env))


def test_database_password_is_validated_through_the_url():
    env = valid_local_demo()
    env["DATABASE_URL"] = "postgresql://usa_user:change-me@db:5432/usa_db"
    assert any("DATABASE_URL" in error for error in validate(env))
    env["DATABASE_URL"] = "sqlite:///db.sqlite3"
    assert any("postgresql" in error for error in validate(env))


def test_cookie_and_transport_flags_must_be_explicit():
    env = valid_local_demo()
    env.pop("COOKIE_SECURE")
    assert any("COOKIE_SECURE" in error for error in validate(env))
    env = valid_local_demo()
    env["SECURE_SSL_REDIRECT"] = "true"
    assert any("SECURE_SSL_REDIRECT" in error for error in validate(env))
    env = valid_local_demo()
    env["SECURE_HSTS_SECONDS"] = "31536000"
    assert any("SECURE_HSTS_SECONDS" in error for error in validate(env))


def test_release_mode_requires_https_flags():
    env = valid_local_demo()
    env["DEPLOYMENT_MODE"] = "release"
    assert any("COOKIE_SECURE" in error for error in validate(env))
    env.update(
        {"COOKIE_SECURE": "true", "SECURE_SSL_REDIRECT": "true", "SECURE_HSTS_SECONDS": "31536000"}
    )
    assert validate(env) == []


def test_celery_eager_mode_is_refused():
    env = valid_local_demo()
    env["CELERY_TASK_ALWAYS_EAGER"] = "true"
    assert any("CELERY_TASK_ALWAYS_EAGER" in error for error in validate(env))


def test_ai_provider_is_explicit_and_groq_needs_a_key():
    env = valid_local_demo()
    env["AI_PROVIDER"] = ""
    assert any("AI_PROVIDER" in error for error in validate(env))
    env["AI_PROVIDER"] = "groq"
    assert any("AI_PROVIDER_API_KEY" in error for error in validate(env))
    env["AI_PROVIDER_API_KEY"] = "g" * 40
    assert validate(env) == []


def test_demo_password_is_required_only_when_demo_mode_is_on():
    env = valid_local_demo()
    env["DEMO_PASSWORD"] = "short"
    assert any("DEMO_PASSWORD" in error for error in validate(env))
    env["DEMO_MODE"] = "false"
    assert validate(env) == []


def test_demo_password_rejects_the_old_public_value():
    env = valid_local_demo()
    # Split so the removed public literal never appears verbatim in the tree.
    env["DEMO_PASSWORD"] = "Demo-" + "Passw0rd!"
    assert any("DEMO_PASSWORD" in error for error in validate(env))


def test_errors_never_contain_secret_values():
    env = valid_local_demo()
    env["DATABASE_URL"] = "postgresql://usa_user:topsecret@db:5432/usa_db"
    errors = validate(env)
    assert any("DATABASE_URL" in error for error in errors)
    assert "topsecret" not in " ".join(errors)
