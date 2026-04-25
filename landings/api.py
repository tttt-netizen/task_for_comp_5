import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

from landings.schemas import LeadAcceptedResponse, LeadIn
from settings import get_settings
from shared.security import get_current_affiliate_id

router = APIRouter()
settings = get_settings()

DEDUP_AND_ENQUEUE_LUA = """
local dedup_key = KEYS[1]
local stream_name = KEYS[2]
local ttl = tonumber(ARGV[1])
local name = ARGV[2]
local phone = ARGV[3]
local country = ARGV[4]
local offer_id = ARGV[5]
local affiliate_id = ARGV[6]

local set_result = redis.call('SET', dedup_key, '1', 'NX', 'EX', ttl)
if not set_result then
  return {0, ''}
end

local message_id = redis.call(
  'XADD',
  stream_name,
  '*',
  'name', name,
  'phone', phone,
  'country', country,
  'offer_id', offer_id,
  'affiliate_id', affiliate_id
)

return {1, message_id}
"""


async def get_redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


@router.post("/lead", response_model=LeadAcceptedResponse)
async def create_lead(
    payload: LeadIn,
    current_affiliate_id: int = Depends(get_current_affiliate_id),
    redis: Redis = Depends(get_redis),
) -> LeadAcceptedResponse:
    if payload.affiliate_id != current_affiliate_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="affiliate_id mismatch")

    dedup_fingerprint = _build_dedup_fingerprint(
        payload.name, payload.phone, payload.offer_id, payload.affiliate_id
    )
    dedup_key = f"dedup:{payload.affiliate_id}:{payload.offer_id}:{dedup_fingerprint}"
    try:
        result = await redis.eval(
            DEDUP_AND_ENQUEUE_LUA,
            2,
            dedup_key,
            settings.redis_stream_name,
            str(settings.redis_dedup_ttl_seconds),
            payload.name,
            payload.phone,
            payload.country,
            str(payload.offer_id),
            str(payload.affiliate_id),
        )
    except RedisError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Queue unavailable") from exc
    finally:
        await redis.aclose()

    if not result or int(result[0]) == 0:
        return LeadAcceptedResponse(status="duplicate")
    return LeadAcceptedResponse()


def _build_dedup_fingerprint(name: str, phone: str, offer_id: int, affiliate_id: int) -> str:
    payload = f"{name.strip().lower()}|{phone.strip()}|{offer_id}|{affiliate_id}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
