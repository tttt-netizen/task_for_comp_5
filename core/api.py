from collections import defaultdict
from datetime import UTC, date, datetime, time

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.schemas import (
    GroupBy,
    LeadItem,
    LeadsAnalyticsResponse,
    LeadsGroup,
    TokenIssueRequest,
    TokenIssueResponse,
)
from settings import get_settings
from shared.db import get_db_session
from shared.models import Affiliate, Lead, Offer
from shared.security import create_access_token, get_current_affiliate_id

router = APIRouter()
settings = get_settings()


@router.post("/auth/token", response_model=TokenIssueResponse)
async def issue_token(
    payload: TokenIssueRequest,
    db: AsyncSession = Depends(get_db_session),
    x_admin_secret: str = Header(default="", alias="X-Admin-Secret"),
) -> TokenIssueResponse:
    if x_admin_secret != settings.token_issuer_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin secret")
    result = await db.execute(select(Affiliate.id).where(Affiliate.id == payload.affiliate_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Affiliate not found")
    return TokenIssueResponse(access_token=create_access_token(payload.affiliate_id))


@router.get("/leads", response_model=LeadsAnalyticsResponse)
async def get_leads_analytics(
    date_from: date = Query(...),
    date_to: date = Query(...),
    group: GroupBy = Query(...),
    affiliate_id: int = Depends(get_current_affiliate_id),
    db: AsyncSession = Depends(get_db_session),
) -> LeadsAnalyticsResponse:
    if date_from > date_to:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="date_from must be <= date_to")

    from_dt = datetime.combine(date_from, time.min).replace(tzinfo=UTC)
    to_dt = datetime.combine(date_to, time.max).replace(tzinfo=UTC)

    statement: Select = (
        select(Lead)
        .options(joinedload(Lead.offer))
        .where(
            and_(
                Lead.affiliate_id == affiliate_id,
                Lead.created_at >= from_dt,
                Lead.created_at <= to_dt,
            )
        )
        .order_by(Lead.created_at.asc())
    )
    result = await db.execute(statement)
    leads = result.scalars().all()

    grouped: dict[str, list[Lead]] = defaultdict(list)
    if group == GroupBy.date:
        for lead in leads:
            grouped[lead.created_at.date().isoformat()].append(lead)
    else:
        offer_map = await _offers_map(db)
        for lead in leads:
            grouped[offer_map.get(lead.offer_id, f"offer_{lead.offer_id}")].append(lead)

    groups = [
        LeadsGroup(
            key=key,
            count=len(group_leads),
            items=[
                LeadItem(
                    id=item.id,
                    name=item.name,
                    phone=item.phone,
                    country=item.country,
                    offer_id=item.offer_id,
                    affiliate_id=item.affiliate_id,
                    created_at=item.created_at.isoformat(),
                )
                for item in group_leads
            ],
        )
        for key, group_leads in sorted(grouped.items(), key=lambda pair: pair[0])
    ]

    return LeadsAnalyticsResponse(
        affiliate_id=affiliate_id,
        date_from=date_from,
        date_to=date_to,
        group=group,
        groups=groups,
    )


async def _offers_map(db: AsyncSession) -> dict[int, str]:
    offers = await db.execute(select(Offer.id, Offer.name))
    return {offer_id: name for offer_id, name in offers.all()}
