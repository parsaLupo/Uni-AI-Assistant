"""Enable pg_trgm for Persian trigram search (architecture.md C-05).

PostgreSQL only — a no-op on SQLite, which stays the dependency-free default
for local test runs (backend/conftest.py; pipeline.md P-06 says the real
engines must also be exercised, which CI and TEST_DATABASE_URL runs do).
"""

from django.db import migrations


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ("common", "0001_enable_pgvector"),
    ]

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql":
            return
        schema_editor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        # Extensions are shared cluster-wide; dropping on unmount would be rude.
        pass
