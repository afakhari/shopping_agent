"""Add a PostgreSQL trigram index when the deployment supports pg_trgm.

The catalog remains functional without this optional index (e.g. SQLite tests or
managed PostgreSQL plans that disallow extension creation). The migration records
no model state because the index is a performance-only implementation detail.
"""
import logging

from django.db import DatabaseError, migrations

logger = logging.getLogger(__name__)


def add_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    try:
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS product_title_trgm_idx "
                "ON catalog_product USING gin (normalized_title gin_trgm_ops)"
            )
    except DatabaseError as exc:
        # Keep deploys working in managed databases without extension privileges.
        logger.warning("Optional pg_trgm index was not created (%s)", type(exc).__name__)


def remove_index(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("DROP INDEX IF EXISTS product_title_trgm_idx")


class Migration(migrations.Migration):
    atomic = False
    dependencies = [("catalog", "0001_initial")]
    operations = [migrations.RunPython(add_index, remove_index)]
