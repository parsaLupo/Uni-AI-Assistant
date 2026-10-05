"""Enable the pgvector extension on PostgreSQL (Phase 02 — "pgvector is available").

ADR-002 makes PostgreSQL + pgvector the single primary store, and the extension
must exist in *every* database the app touches (dev, CI, staging, production) —
including the databases pytest-django creates. Doing it in a migration means
``manage.py migrate`` is sufficient; no manual psql step can be forgotten.

The guard makes the operation a no-op on SQLite, which remains the default for
local test runs (conftest.py).
"""

from django.db import migrations


class _PostgreSQLOnly(migrations.RunSQL):
    """Run SQL only when the target database is PostgreSQL."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == "postgresql":
            super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == "postgresql":
            super().database_backwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):
    initial = False

    dependencies = []

    operations = [
        _PostgreSQLOnly(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="DROP EXTENSION IF EXISTS vector;",
        )
    ]
