from pydantic import BaseModel, ConfigDict, Field, field_validator


class LeadIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Oleksii",
                "phone": "+380982342123",
                "country": "UA",
                "offer_id": 1,
                "affiliate_id": 100,
            }
        }
    )

    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=3, max_length=64)
    country: str = Field(min_length=2, max_length=2)
    offer_id: int
    affiliate_id: int

    @field_validator("name", "phone")
    @classmethod
    def strip_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be empty")
        return cleaned

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str) -> str:
        country = value.strip().upper()
        if len(country) != 2 or not country.isalpha():
            raise ValueError("country must be ISO 3166-1 alpha-2 code")
        return country


class LeadAcceptedResponse(BaseModel):
    status: str = "accepted"
