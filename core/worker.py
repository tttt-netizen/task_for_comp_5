import asyncio
import logging
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from redis.exceptions import ResponseError
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError

from settings import get_settings
from shared.db import AsyncSessionLocal
from shared.models import Affiliate, Lead, Offer, ProcessedEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("core-worker")
settings = get_settings()


async def run_worker() -> None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await _ensure_consumer_group(redis)
    while True:
        try:
            await _reclaim_pending(redis)
            response = await redis.xreadgroup(
                groupname=settings.redis_consumer_group,
                consumername=settings.redis_consumer_name,
                streams={settings.redis_stream_name: ">"},
                count=settings.redis_read_count,
                block=settings.redis_read_block_ms,
            )
            if not response:
                await asyncio.sleep(0.1)
                continue

            for _, messages in response:
                for message_id, fields in messages:
                    try:
                        await process_stream_entry(message_id, fields)
                    except Exception:
                        logger.exception("Failed stream message id=%s", message_id)
                        await redis.xadd(
                            settings.redis_dead_letter_stream,
                            {"event_id": message_id, "reason": "worker_processing_error"},
                        )
                    finally:
                        await redis.xack(settings.redis_stream_name, settings.redis_consumer_group, message_id)
        except Exception:
            logger.exception("Worker loop failed")
            await asyncio.sleep(1)


async def process_stream_entry(event_id: str, lead_data: dict) -> str:
    offer_id = int(lead_data["offer_id"])
    affiliate_id = int(lead_data["affiliate_id"])
    async with AsyncSessionLocal() as session:
        marker = ProcessedEvent(event_id=event_id)
        session.add(marker)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            return "skipped: duplicate event id"

        if not await _entity_exists(session, Offer, offer_id):
            await session.commit()
            return "failed: unknown offer_id"
        if not await _entity_exists(session, Affiliate, affiliate_id):
            await session.commit()
            return "failed: unknown affiliate_id"

        dedup_from = datetime.now(UTC) - timedelta(minutes=10)
        duplicate_check = await session.execute(
            select(Lead.id).where(
                and_(
                    Lead.name == lead_data["name"],
                    Lead.phone == lead_data["phone"],
                    Lead.offer_id == offer_id,
                    Lead.affiliate_id == affiliate_id,
                    Lead.created_at >= dedup_from,
                )
            )
        )
        if duplicate_check.scalar_one_or_none() is not None:
            await session.commit()
            return "skipped: duplicate in 10 minute window"

        session.add(
            Lead(
                name=lead_data["name"],
                phone=lead_data["phone"],
                country=lead_data["country"],
                offer_id=offer_id,
                affiliate_id=affiliate_id,
            )
        )
        await session.commit()
        return "accepted"


async def _entity_exists(session, model, entity_id: int) -> bool:
    result = await session.execute(select(model.id).where(model.id == entity_id))
    return result.scalar_one_or_none() is not None


async def _ensure_consumer_group(redis: Redis) -> None:
    try:
        await redis.xgroup_create(
            name=settings.redis_stream_name,
            groupname=settings.redis_consumer_group,
            id="0",
            mkstream=True,
        )
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def _reclaim_pending(redis: Redis) -> None:
    await redis.xautoclaim(
        name=settings.redis_stream_name,
        groupname=settings.redis_consumer_group,
        consumername=settings.redis_consumer_name,
        min_idle_time=settings.redis_pending_idle_ms,
        start_id="0-0",
        count=settings.redis_read_count,
    )


if __name__ == "__main__":
    asyncio.run(run_worker())
