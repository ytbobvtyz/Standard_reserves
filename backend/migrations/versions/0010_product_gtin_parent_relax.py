"""Allow duplicate GTIN; drop parent/children FKs.

Revision ID: 0010_product_gtin_parent_relax
Revises: 0009_balance_unit_kg
Create Date: 2026-08-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010_product_gtin_parent_relax"
down_revision: str | Sequence[str] | None = "0009_balance_unit_kg"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS products_gtin_key;")
    op.execute("DROP INDEX IF EXISTS idx_products_gtin;")
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_gtin
            ON products(gtin) WHERE gtin IS NOT NULL;
        """)
    op.execute("""
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_attribute att
                    ON att.attrelid = con.conrelid
                    AND att.attnum = ANY (con.conkey)
                WHERE con.conrelid = 'products'::regclass
                  AND con.contype = 'f'
                  AND att.attname IN ('parent_code', 'children_code')
            LOOP
                EXECUTE format(
                    'ALTER TABLE products DROP CONSTRAINT %I',
                    r.conname
                );
            END LOOP;
        END $$;
        """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE products
            ADD CONSTRAINT products_parent_code_fkey
            FOREIGN KEY (parent_code) REFERENCES products(code);
        """)
    op.execute("""
        ALTER TABLE products
            ADD CONSTRAINT products_children_code_fkey
            FOREIGN KEY (children_code) REFERENCES products(code);
        """)
    op.execute("DROP INDEX IF EXISTS idx_products_gtin;")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_products_gtin
            ON products(gtin) WHERE gtin IS NOT NULL;
        """)
