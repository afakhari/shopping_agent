"""Optionally accelerate Django icontains on the 225k-product Persian catalog.

Django's PostgreSQL icontains lookup applies UPPER(column) in SQL; the
0002 index on the raw normalized_title expression may not serve that query.
Add GIN trigram indexes on the *actual expression* for each OR branch.
No index on source price/offer data is removed. Skips non-PostgreSQL DBs.

CREATE INDEX CONCURRENTLY avoids blocking routine data writes. RunPython
without migration atomicity is required by PostgreSQL for CONCURRENTLY.
"""
from __future__ import annotations

import logging

from django.db import DatabaseError, migrations

logger = logging.getLogger(__name__)

_INDEXES = (
    ("product_title_ci_trgm_idx", "normalized_title"),
    ("product_category_ci_trgm_idx", "category_name"),
    ("product_brand_ci_trgm_idx", "brand_name"),
    ("product_model_ci_trgm_idx", "model"),
)


def _extension_ready(cursor):
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    except DatabaseError as exc:
        logger.warning("Optional pg_trgm unavailable (%s); search remains functional", type(exc).__name__)
        return False
    return True


def add_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        if not _extension_ready(cursor):
            return
        for name, column in _INDEXES:
            try:
                # Explicit static identifiers only, never user-controlled SQL.
                cursor.execute(
                    f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} "
                    f"ON catalog_product USING gin (UPPER({column}) gin_trgm_ops)"
                )
            except DatabaseError as exc:
                logger.warning("Optional search index %s unavailable (%s)", name, type(exc).__name__)


def drop_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for name, _ in _INDEXES:
            cursor.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")


class Migration(migrations.Migration):
    atomic = False
    dependencies = [("catalog", "0004_alter_offer_product_alter_offer_shop")]
    operations = [migrations.RunPython(add_indexes, drop_indexes)]
