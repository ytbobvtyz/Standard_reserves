from app.models import (
    AvailableBalance,
    Base,
    Event,
    Normative,
    Object,
    PasswordResetToken,
    Product,
    Request,
    RequestItem,
    RequestItemHistory,
    Session,
    User,
)

EXPECTED_TABLES = {
    "available_balances",
    "events",
    "normatives",
    "objects",
    "password_reset_tokens",
    "products",
    "request_item_history",
    "request_items",
    "requests",
    "sessions",
    "users",
}


def test_models_import() -> None:
    assert Product.__tablename__ == "products"
    assert Object.__tablename__ == "objects"
    assert User.__tablename__ == "users"
    assert Session.__tablename__ == "sessions"
    assert PasswordResetToken.__tablename__ == "password_reset_tokens"
    assert Request.__tablename__ == "requests"
    assert RequestItem.__tablename__ == "request_items"
    assert RequestItemHistory.__tablename__ == "request_item_history"
    assert Normative.__tablename__ == "normatives"
    assert AvailableBalance.__tablename__ == "available_balances"
    assert Event.__tablename__ == "events"


def test_all_tables_registered() -> None:
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_cascade_foreign_keys() -> None:
    session_fk = next(iter(Session.__table__.c.user_id.foreign_keys))
    assert session_fk.ondelete == "CASCADE"

    reset_fk = next(iter(PasswordResetToken.__table__.c.user_id.foreign_keys))
    assert reset_fk.ondelete == "CASCADE"

    item_fk = next(iter(RequestItem.__table__.c.request_id.foreign_keys))
    assert item_fk.ondelete == "CASCADE"

    history_fk = next(iter(RequestItemHistory.__table__.c.request_item_id.foreign_keys))
    assert history_fk.ondelete == "CASCADE"
