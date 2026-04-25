from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from settings import get_settings
from shared.db import get_db_session
from shared.models import Affiliate

settings = get_settings()


def create_access_token(affiliate_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {"id": affiliate_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


async def get_current_affiliate_id(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db_session),
) -> int:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
        )

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token)
    affiliate_id = payload.get("id")
    if not isinstance(affiliate_id, int):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload must include integer id",
        )

    result = await db.execute(select(Affiliate.id).where(Affiliate.id == affiliate_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Affiliate does not exist",
        )

    return affiliate_id
