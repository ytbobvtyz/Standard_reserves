"""Create all application tables.

Revision ID: 0001_create_tables
Revises:
Create Date: 2026-08-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_create_tables"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE objects (
            code INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            region TEXT,
            address TEXT,
            type VARCHAR(20) NOT NULL CHECK (type IN ('plant', 'warehouse')),
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITH TIME ZONE
        );
        """)
    op.execute("""
        CREATE TABLE products (
            code INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            category CHAR(1) NOT NULL CHECK (category IN ('A', 'B', 'C')),
            plant_id INTEGER NOT NULL REFERENCES objects(code),
            second_plant_id INTEGER REFERENCES objects(code),
            third_plant_id INTEGER REFERENCES objects(code),
            weight_kg DECIMAL(12,4) NOT NULL,
            monthly_consumption DECIMAL(12,2),
            is_active BOOLEAN NOT NULL DEFAULT true,
            parent_code INTEGER REFERENCES products(code),
            children_code INTEGER REFERENCES products(code),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITH TIME ZONE
        );
        """)
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role VARCHAR(30) NOT NULL CHECK (role IN (
                'commercial', 'pp', 'economist', 'logistics', 'guest'
            )),
            department TEXT,
            is_active BOOLEAN NOT NULL DEFAULT true,
            last_login_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITH TIME ZONE
        );
        """)
    op.execute("""
        CREATE TABLE sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token TEXT NOT NULL UNIQUE,
            ip_address INET,
            user_agent TEXT,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            revoked_at TIMESTAMP WITH TIME ZONE
        );
        """)
    op.execute("""
        CREATE TABLE password_reset_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            used BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        """)
    op.execute("""
        CREATE TABLE requests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_type VARCHAR(20) NOT NULL CHECK (
                request_type IN ('normative', 'one_time')
            ),
            status VARCHAR(30) NOT NULL DEFAULT 'draft' CHECK (status IN (
                'draft',
                'pp_approved',
                'economy_check',
                'pp_rework',
                'economy_rework',
                'active',
                'approved',
                'rejected',
                'expired',
                'executed'
            )),
            client_name TEXT NOT NULL,
            initiator_id UUID NOT NULL REFERENCES users(id),
            initiator_comment TEXT,
            comment_pp TEXT,
            comment_economy TEXT,
            expiry_date DATE,
            approved_at TIMESTAMP WITH TIME ZONE,
            executed_at TIMESTAMP WITH TIME ZONE,
            pp_approved_at TIMESTAMP WITH TIME ZONE,
            pp_approved_by UUID REFERENCES users(id),
            pp_action VARCHAR(20) CHECK (
                pp_action IN ('approve', 'reject', 'edit')
            ),
            economy_approved_at TIMESTAMP WITH TIME ZONE,
            economy_approved_by UUID REFERENCES users(id),
            economy_action VARCHAR(20) CHECK (
                economy_action IN ('approve', 'reject', 'edit')
            ),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITH TIME ZONE
        );
        """)
    op.execute("""
        CREATE TABLE request_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id UUID NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
            product_code INTEGER NOT NULL REFERENCES products(code),
            warehouse_code INTEGER NOT NULL REFERENCES objects(code),
            quantity_requested DECIMAL(12,2) NOT NULL
                CHECK (quantity_requested > 0),
            quantity_approved DECIMAL(12,2),
            unit VARCHAR(10) NOT NULL CHECK (unit IN ('шт', 'т')),
            comment TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            UNIQUE (request_id, product_code, warehouse_code)
        );
        """)
    op.execute("""
        CREATE TABLE request_item_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_item_id UUID NOT NULL
                REFERENCES request_items(id) ON DELETE CASCADE,
            field_name VARCHAR(30) NOT NULL CHECK (
                field_name IN ('quantity_requested', 'quantity_approved')
            ),
            old_value DECIMAL(12,2),
            new_value DECIMAL(12,2),
            changed_by UUID NOT NULL REFERENCES users(id),
            changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            comment TEXT
        );
        """)
    op.execute("""
        CREATE TABLE normatives (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id UUID NOT NULL REFERENCES requests(id),
            product_code INTEGER NOT NULL REFERENCES products(code),
            warehouse_code INTEGER NOT NULL REFERENCES objects(code),
            quantity DECIMAL(12,2) NOT NULL,
            unit VARCHAR(10) NOT NULL CHECK (unit IN ('шт', 'т')),
            client_name TEXT NOT NULL,
            expiry_date DATE NOT NULL,
            category CHAR(1) NOT NULL CHECK (category IN ('A', 'B', 'C')),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITH TIME ZONE
        );
        """)
    op.execute("""
        CREATE TABLE available_balances (
            warehouse_code INTEGER NOT NULL REFERENCES objects(code),
            product_code INTEGER NOT NULL REFERENCES products(code),
            quantity DECIMAL(12,2) NOT NULL DEFAULT 0,
            unit VARCHAR(10) NOT NULL DEFAULT 'шт' CHECK (unit IN ('шт', 'т')),
            last_sync_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            source VARCHAR(50) DEFAULT 'manual',
            PRIMARY KEY (warehouse_code, product_code)
        );
        """)
    op.execute("""
        CREATE TABLE events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type VARCHAR(50) NOT NULL CHECK (event_type IN (
                'request_created',
                'request_approved',
                'request_rejected',
                'normative_active',
                'normative_expired',
                'deficit_detected',
                'deficit_resolved'
            )),
            request_id UUID REFERENCES requests(id),
            payload JSONB NOT NULL,
            processed BOOLEAN NOT NULL DEFAULT false,
            processed_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS events CASCADE;")
    op.execute("DROP TABLE IF EXISTS available_balances CASCADE;")
    op.execute("DROP TABLE IF EXISTS normatives CASCADE;")
    op.execute("DROP TABLE IF EXISTS request_item_history CASCADE;")
    op.execute("DROP TABLE IF EXISTS request_items CASCADE;")
    op.execute("DROP TABLE IF EXISTS requests CASCADE;")
    op.execute("DROP TABLE IF EXISTS password_reset_tokens CASCADE;")
    op.execute("DROP TABLE IF EXISTS sessions CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")
    op.execute("DROP TABLE IF EXISTS products CASCADE;")
    op.execute("DROP TABLE IF EXISTS objects CASCADE;")
