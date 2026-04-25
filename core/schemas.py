from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class GroupBy(str, Enum):
    date = "date"
    offer = "offer"


class TokenIssueRequest(BaseModel):
    affiliate_id: int = Field(gt=0)


class TokenIssueResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LeadItem(BaseModel):
    id: int
    name: str
    phone: str
    country: str
    offer_id: int
    affiliate_id: int
    created_at: str


class LeadsGroup(BaseModel):
    key: str
    count: int
    items: list[LeadItem]


class LeadsAnalyticsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "affiliate_id": 100,
                "date_from": "2026-04-01",
                "date_to": "2026-04-30",
                "group": "date",
                "groups": [{"key": "2026-04-25", "count": 2, "items": []}],
            }
        }
    )

    affiliate_id: int
    date_from: date
    date_to: date
    group: GroupBy
    groups: list[LeadsGroup]
