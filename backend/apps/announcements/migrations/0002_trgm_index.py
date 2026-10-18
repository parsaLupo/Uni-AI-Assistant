"""PostgreSQL-only trigram index over announcement titles (C-05). No-op on SQLite."""

from django.db import migrations


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ("announcements", "0001_initial"),
        ("common", "0002_enable_pg_trgm"),
    ]

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql":
            return
        schema_editor.execute(
            "CREATE INDEX IF NOT EXISTS announcements_normalized_title_trgm "
            "ON announcements_announcement USING GIN (normalized_title gin_trgm_ops)"
        )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql":
            return
        schema_editor.execute("DROP INDEX IF EXISTS announcements_normalized_title_trgm")
