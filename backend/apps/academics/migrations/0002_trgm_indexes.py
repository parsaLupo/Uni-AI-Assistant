"""PostgreSQL-only trigram indexes over normalized names (C-05).

A no-op on SQLite; the ILIKE-style `icontains` still works there, while
PostgreSQL accelerates it with GIN/gin_trgm_ops.
"""

from django.db import migrations

INDEXES = {
    "academics_faculty_normalized_name_trgm": "normalized_name",
    "academics_department_normalized_name_trgm": "normalized_name",
}


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ("academics", "0001_initial"),
        ("common", "0002_enable_pg_trgm"),
    ]

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql":
            return
        for index_name, column in INDEXES.items():
            table = {
                "academics_faculty_normalized_name_trgm": "academics_faculty",
                "academics_department_normalized_name_trgm": "academics_department",
            }[index_name]
            schema_editor.execute(
                f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} "
                f"USING GIN ({column} gin_trgm_ops)"
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql":
            return
        for index_name in INDEXES:
            schema_editor.execute(f"DROP INDEX IF EXISTS {index_name}")
