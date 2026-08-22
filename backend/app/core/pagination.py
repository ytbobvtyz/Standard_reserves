from sqlalchemy import Select


def paginate(stmt: Select, page: int, limit: int) -> Select:
    return stmt.offset((page - 1) * limit).limit(limit)
