import asyncio
import json
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User


def _server_secret() -> str:
    with open("/proc/1/environ", "rb") as handle:
        env = handle.read().split(b"\0")
    for item in env:
        if item.startswith(b"SECRET_KEY="):
            return item.split(b"=", 1)[1].decode()
    raise RuntimeError("SECRET_KEY is not in the server process")


async def main() -> None:
    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(
                select(User).where(User.role == "logistics", User.deleted_at.is_(None))
            )
        ).scalars().first()
    if user is None:
        print("no logistics user")
        return
    token = jwt.encode(
        {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        _server_secret(),
        algorithm="HS256",
    )
    request = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/logistics/normative/dashboard?"
        + urllib.parse.urlencode(
            {"warehouse_code": 2001, "filter_mode": "all", "unit": "шт"}
        ),
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = json.load(response)
    items = body["data"][0]["deficit_items"]
    keys = sorted(items[0].keys())
    print("keys", "no_ready" in keys, "ready" in keys, "collected" in keys, "on_way" in keys)
    nonzero = 0
    sample = None
    for item in items:
        parts = [item.get("no_ready"), item.get("ready"), item.get("collected"), item.get("on_way")]
        if any(part not in (0, 0.0, None) for part in parts):
            nonzero += 1
            if sample is None:
                sample = {
                    "product_code": item["product_code"],
                    "available": item["available"],
                    "no_ready": item.get("no_ready"),
                    "ready": item.get("ready"),
                    "collected": item.get("collected"),
                    "on_way": item.get("on_way"),
                    "plan": item["plan"],
                    "weight_kg": item.get("weight_kg"),
                }
    print("items", len(items), "nonzero", nonzero)
    print(sample)


if __name__ == "__main__":
    asyncio.run(main())
