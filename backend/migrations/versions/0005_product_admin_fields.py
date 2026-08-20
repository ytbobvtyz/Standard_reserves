"""Add product admin fields and audit_log.

Revision ID: 0005_product_admin_fields
Revises: 0004_one_time_execute_fields
Create Date: 2026-08-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_product_admin_fields"
down_revision: str | Sequence[str] | None = "0004_one_time_execute_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE products
            ADD COLUMN IF NOT EXISTS gtin VARCHAR(13);
        """)
    op.execute("""
        ALTER TABLE products
            ADD COLUMN IF NOT EXISTS mark_control BOOLEAN NOT NULL DEFAULT false;
        """)
    op.execute("""
        ALTER TABLE products
            ADD COLUMN IF NOT EXISTS last_modified_by UUID REFERENCES users(id);
        """)
    op.execute("""
        ALTER TABLE products
            ADD COLUMN IF NOT EXISTS last_modified_at TIMESTAMP WITH TIME ZONE
            DEFAULT NOW();
        """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_products_gtin
            ON products(gtin) WHERE gtin IS NOT NULL;
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_last_modified_at
            ON products(last_modified_at);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_last_modified_by
            ON products(last_modified_by);
        """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_products_gtin'
            ) THEN
                ALTER TABLE products
                    ADD CONSTRAINT ck_products_gtin
                    CHECK (gtin IS NULL OR gtin ~ '^[0-9]{13}$');
            END IF;
        END $$;
        """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            action TEXT NOT NULL,
            changed_by UUID REFERENCES users(id),
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_log_entity
            ON audit_log(entity_type, entity_id);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_log_changed_by
            ON audit_log(changed_by);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_log_created_at
            ON audit_log(created_at);
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE;")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS ck_products_gtin;")
    op.execute("DROP INDEX IF EXISTS idx_products_last_modified_by;")
    op.execute("DROP INDEX IF EXISTS idx_products_last_modified_at;")
    op.execute("DROP INDEX IF EXISTS idx_products_gtin;")
    op.execute("""
        ALTER TABLE products
            DROP COLUMN IF EXISTS last_modified_at,
            DROP COLUMN IF EXISTS last_modified_by,
            DROP COLUMN IF EXISTS mark_control,
            DROP COLUMN IF EXISTS gtin;
        """)
