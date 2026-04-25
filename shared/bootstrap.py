from sqlalchemy import select

from shared.db import AsyncSessionLocal
from shared.models import Affiliate, Offer

DEFAULT_OFFERS = [
    Offer(id=1, name="Beauty Product"),
    Offer(id=2, name="Fitness Product"),
]

DEFAULT_AFFILIATES = [
    Affiliate(id=100, name="Affiliate Alpha"),
    Affiliate(id=200, name="Affiliate Beta"),
]


async def seed_reference_data() -> None:
    async with AsyncSessionLocal() as session:
        for offer in DEFAULT_OFFERS:
            existing = await session.execute(select(Offer.id).where(Offer.id == offer.id))
            if existing.scalar_one_or_none() is None:
                session.add(Offer(id=offer.id, name=offer.name))

        for affiliate in DEFAULT_AFFILIATES:
            existing = await session.execute(
                select(Affiliate.id).where(Affiliate.id == affiliate.id)
            )
            if existing.scalar_one_or_none() is None:
                session.add(Affiliate(id=affiliate.id, name=affiliate.name))

        await session.commit()


async def add_affiliate(affiliate_id: int, name: str) -> bool:
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(Affiliate.id).where(Affiliate.id == affiliate_id))
        if existing.scalar_one_or_none() is not None:
            return False
        session.add(Affiliate(id=affiliate_id, name=name))
        await session.commit()
        return True


async def list_affiliates() -> list[tuple[int, str]]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Affiliate.id, Affiliate.name).order_by(Affiliate.id.asc()))
        return [(affiliate_id, name) for affiliate_id, name in result.all()]


async def list_offers() -> list[tuple[int, str]]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Offer.id, Offer.name).order_by(Offer.id.asc()))
        return [(offer_id, name) for offer_id, name in result.all()]
