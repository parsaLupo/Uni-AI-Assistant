"""PostgreSQL-only trigram index over course titles (C-05). No-op on SQLite."""

from django.db import migrations


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ("courses", "0001_initial"),
        ("common", "0002_enable_pg_trgm"),
    ]

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql":
            return
        schema_editor.execute(
            "CREATE INDEX IF NOT EXISTS courses_normalized_title_trgm "
            "ON courses_course USING GIN (normalized_title gin_trgm_ops)"
        )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql":
            return
        schema_editor.execute("DROP INDEX IF EXISTS courses_normalized_title_trgm")
