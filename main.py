import argparse
import asyncio
import random
import subprocess
import sys
from datetime import date, timedelta

import httpx
from redis.asyncio import Redis
from sqlalchemy import text
import uvicorn

from core.worker import run_worker
from shared.bootstrap import add_affiliate, list_affiliates, list_offers, seed_reference_data
from shared.db import AsyncSessionLocal
from shared.security import create_access_token
from settings import get_settings

settings = get_settings()


def _run_alembic_upgrade() -> None:
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


def init() -> None:
    _run_alembic_upgrade()
    asyncio.run(seed_reference_data())
    print("Init complete.")


def start_landings() -> None:
    uvicorn.run("landings.main:app", host="0.0.0.0", port=8000)


def start_core() -> None:
    uvicorn.run("core.main:app", host="0.0.0.0", port=8001)


def start_worker() -> None:
    asyncio.run(run_worker())


def generate_token(affiliate_id: int) -> None:
    print(create_access_token(affiliate_id))


def create_affiliate(affiliate_id: int, name: str, print_token: bool) -> None:
    created = asyncio.run(add_affiliate(affiliate_id, name))
    if created:
        print(f"Affiliate added: id={affiliate_id}, name={name}")
    else:
        print(f"Affiliate already exists: id={affiliate_id}")
    if print_token:
        print("Token:")
        print(create_access_token(affiliate_id))


def show_affiliates() -> None:
    items = asyncio.run(list_affiliates())
    if not items:
        print("No affiliates found.")
        return
    for affiliate_id, name in items:
        print(f"{affiliate_id}\t{name}")


def show_offers() -> None:
    items = asyncio.run(list_offers())
    if not items:
        print("No offers found.")
        return
    for offer_id, name in items:
        print(f"{offer_id}\t{name}")


def check_connections() -> None:
    ok = asyncio.run(_check_connections_async())
    if not ok:
        raise SystemExit(1)


async def _check_connections_async() -> bool:
    db_ok = await _check_db()
    redis_ok = await _check_redis()
    return db_ok and redis_ok


async def _check_db() -> bool:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        print("DB: OK")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"DB: FAIL ({exc})")
        return False


async def _check_redis() -> bool:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        pong = await redis.ping()
        if pong:
            print("REDIS: OK")
            return True
        print("REDIS: FAIL (ping returned false)")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"REDIS: FAIL ({exc})")
        return False
    finally:
        await redis.aclose()


def _resolve_token(token: str | None, affiliate_id: int | None) -> str:
    if token:
        return token
    if affiliate_id is not None:
        return create_access_token(affiliate_id)
    raise ValueError("Provide --token or --affiliate-id")


async def get_leads(
    token: str | None,
    affiliate_id: int | None,
    date_from: str,
    date_to: str,
    group: str,
) -> None:
    auth_token = _resolve_token(token, affiliate_id)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "http://localhost:8001/leads",
            params={"date_from": date_from, "date_to": date_to, "group": group},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        print(response.status_code)
        print(response.text)


async def loadtest(token: str | None, affiliate_id: int, count: int, concurrency: int) -> None:
    auth_token = _resolve_token(token, affiliate_id)
    countries = ["UA", "PL", "DE", "IT", "ES", "FR", "RO", "CZ"]
    offers = [1, 2]
    semaphore = asyncio.Semaphore(concurrency)
    stats = {"accepted": 0, "duplicate": 0, "other": 0}

    async def send_one(index: int, client: httpx.AsyncClient) -> None:
        async with semaphore:
            payload = {
                "name": f"Lead_{index}_{random.randint(1, 1000)}",
                "phone": f"+3809{random.randint(10000000, 99999999)}",
                "country": random.choice(countries),
                "offer_id": random.choice(offers),
                "affiliate_id": affiliate_id,
            }
            response = await client.post(
                "http://localhost:8000/lead",
                json=payload,
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            if response.status_code == 200 and response.json().get("status", "accepted") in stats:
                stats[response.json().get("status", "accepted")] += 1
            else:
                stats["other"] += 1

    async with httpx.AsyncClient(timeout=60) as client:
        await asyncio.gather(*(send_one(i, client) for i in range(count)))

    print(
        f"Loadtest done: total={count}, accepted={stats['accepted']}, "
        f"duplicate={stats['duplicate']}, other={stats['other']}"
    )


def _default_dates() -> tuple[str, str]:
    today = date.today()
    return (today - timedelta(days=7)).isoformat(), today.isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Main project entrypoint")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")
    sub.add_parser("check")
    sub.add_parser("landings")
    sub.add_parser("core")
    sub.add_parser("worker")

    token_parser = sub.add_parser("token")
    token_parser.add_argument("--affiliate-id", type=int, required=True)

    add_aff = sub.add_parser("add-affiliate")
    add_aff.add_argument("--id", type=int, required=True)
    add_aff.add_argument("--name", required=True)
    add_aff.add_argument("--no-token", action="store_true")

    sub.add_parser("list-affiliates")
    sub.add_parser("list-offers")

    leads_parser = sub.add_parser("leads")
    leads_parser.add_argument("--token")
    leads_parser.add_argument("--affiliate-id", type=int)
    from_default, to_default = _default_dates()
    leads_parser.add_argument("--date-from", default=from_default)
    leads_parser.add_argument("--date-to", default=to_default)
    leads_parser.add_argument("--group", choices=["date", "offer"], default="date")

    load_parser = sub.add_parser("loadtest")
    load_parser.add_argument("--token")
    load_parser.add_argument("--affiliate-id", type=int, required=True)
    load_parser.add_argument("--count", type=int, default=10000)
    load_parser.add_argument("--concurrency", type=int, default=200)

    args = parser.parse_args()
    if args.command == "init":
        init()
    elif args.command == "check":
        check_connections()
    elif args.command == "landings":
        start_landings()
    elif args.command == "core":
        start_core()
    elif args.command == "worker":
        start_worker()
    elif args.command == "token":
        generate_token(args.affiliate_id)
    elif args.command == "add-affiliate":
        create_affiliate(args.id, args.name, print_token=not args.no_token)
    elif args.command == "list-affiliates":
        show_affiliates()
    elif args.command == "list-offers":
        show_offers()
    elif args.command == "leads":
        asyncio.run(get_leads(args.token, args.affiliate_id, args.date_from, args.date_to, args.group))
    elif args.command == "loadtest":
        asyncio.run(loadtest(args.token, args.affiliate_id, args.count, args.concurrency))


if __name__ == "__main__":
    main()
