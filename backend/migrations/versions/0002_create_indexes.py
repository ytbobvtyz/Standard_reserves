"""Create indexes from DATA_MODEL.md.

Revision ID: 0002_create_indexes
Revises: 0001_create_tables
Create Date: 2026-08-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_create_indexes"
down_revision: str | Sequence[str] | None = "0001_create_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE INDEX idx_objects_type ON objects(type);")
    op.execute("CREATE INDEX idx_objects_city ON objects(city);")

    op.execute("CREATE INDEX idx_products_category ON products(category);")
    op.execute("CREATE INDEX idx_products_plant_id ON products(plant_id);")
    op.execute(
        "CREATE INDEX idx_products_is_active ON products(is_active) "
        "WHERE is_active = true;"
    )
    op.execute(
        "CREATE INDEX idx_products_parent_code ON products(parent_code) "
        "WHERE parent_code IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX idx_products_children_code ON products(children_code) "
        "WHERE children_code IS NOT NULL;"
    )

    op.execute("CREATE INDEX idx_users_username ON users(username);")
    op.execute("CREATE INDEX idx_users_email ON users(email);")
    op.execute("CREATE INDEX idx_users_role ON users(role);")
    op.execute(
        "CREATE INDEX idx_users_is_active ON users(is_active) WHERE is_active = true;"
    )

    op.execute("CREATE INDEX idx_sessions_user_id ON sessions(user_id);")
    op.execute("CREATE INDEX idx_sessions_token ON sessions(token);")
    op.execute("CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);")
    op.execute(
        "CREATE INDEX idx_sessions_revoked_at ON sessions(revoked_at) "
        "WHERE revoked_at IS NULL;"
    )

    op.execute(
        "CREATE INDEX idx_password_reset_tokens_user_id "
        "ON password_reset_tokens(user_id);"
    )
    op.execute(
        "CREATE INDEX idx_password_reset_tokens_token ON password_reset_tokens(token);"
    )
    op.execute(
        "CREATE INDEX idx_password_reset_tokens_expires_at "
        "ON password_reset_tokens(expires_at);"
    )

    op.execute(
        "CREATE INDEX idx_requests_status_type ON requests(status, request_type);"
    )
    op.execute("CREATE INDEX idx_requests_initiator_id ON requests(initiator_id);")
    op.execute("CREATE INDEX idx_requests_client_name ON requests(client_name);")
    op.execute("CREATE INDEX idx_requests_created_at ON requests(created_at);")
    op.execute(
        "CREATE INDEX idx_requests_expiry_date ON requests(expiry_date) "
        "WHERE expiry_date IS NOT NULL;"
    )

    op.execute(
        "CREATE INDEX idx_request_items_request_id ON request_items(request_id);"
    )
    op.execute(
        "CREATE INDEX idx_request_items_product_code ON request_items(product_code);"
    )
    op.execute(
        "CREATE INDEX idx_request_items_warehouse_code "
        "ON request_items(warehouse_code);"
    )
    op.execute(
        "CREATE INDEX idx_request_items_product_warehouse "
        "ON request_items(product_code, warehouse_code);"
    )

    op.execute(
        "CREATE INDEX idx_request_item_history_item_id "
        "ON request_item_history(request_item_id);"
    )
    op.execute(
        "CREATE INDEX idx_request_item_history_changed_by "
        "ON request_item_history(changed_by);"
    )

    op.execute(
        "CREATE INDEX idx_normatives_product_warehouse "
        "ON normatives(product_code, warehouse_code);"
    )
    op.execute("CREATE INDEX idx_normatives_product_code ON normatives(product_code);")
    op.execute(
        "CREATE INDEX idx_normatives_warehouse_code ON normatives(warehouse_code);"
    )
    op.execute("CREATE INDEX idx_normatives_expiry_date ON normatives(expiry_date);")
    op.execute(
        "CREATE INDEX idx_normatives_deleted_at ON normatives(deleted_at) "
        "WHERE deleted_at IS NULL;"
    )
    op.execute("CREATE INDEX idx_normatives_created_at ON normatives(created_at);")

    op.execute(
        "CREATE INDEX idx_available_balances_warehouse "
        "ON available_balances(warehouse_code);"
    )
    op.execute(
        "CREATE INDEX idx_available_balances_product "
        "ON available_balances(product_code);"
    )
    op.execute(
        "CREATE INDEX idx_available_balances_quantity ON available_balances(quantity) "
        "WHERE quantity > 0;"
    )

    op.execute(
        "CREATE INDEX idx_events_processed ON events(processed) "
        "WHERE processed = false;"
    )
    op.execute("CREATE INDEX idx_events_request_id ON events(request_id);")
    op.execute("CREATE INDEX idx_events_created_at ON events(created_at);")


def downgrade() -> None:
    indexes = [
        "idx_events_created_at",
        "idx_events_request_id",
        "idx_events_processed",
        "idx_available_balances_quantity",
        "idx_available_balances_product",
        "idx_available_balances_warehouse",
        "idx_normatives_created_at",
        "idx_normatives_deleted_at",
        "idx_normatives_expiry_date",
        "idx_normatives_warehouse_code",
        "idx_normatives_product_code",
        "idx_normatives_product_warehouse",
        "idx_request_item_history_changed_by",
        "idx_request_item_history_item_id",
        "idx_request_items_product_warehouse",
        "idx_request_items_warehouse_code",
        "idx_request_items_product_code",
        "idx_request_items_request_id",
        "idx_requests_expiry_date",
        "idx_requests_created_at",
        "idx_requests_client_name",
        "idx_requests_initiator_id",
        "idx_requests_status_type",
        "idx_password_reset_tokens_expires_at",
        "idx_password_reset_tokens_token",
        "idx_password_reset_tokens_user_id",
        "idx_sessions_revoked_at",
        "idx_sessions_expires_at",
        "idx_sessions_token",
        "idx_sessions_user_id",
        "idx_users_is_active",
        "idx_users_role",
        "idx_users_email",
        "idx_users_username",
        "idx_products_children_code",
        "idx_products_parent_code",
        "idx_products_is_active",
        "idx_products_plant_id",
        "idx_products_category",
        "idx_objects_city",
        "idx_objects_type",
    ]
    for name in indexes:
        op.execute(f"DROP INDEX IF EXISTS {name};")
