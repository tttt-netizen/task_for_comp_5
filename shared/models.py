from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    leads: Mapped[list["Lead"]] = relationship(back_populates="offer")


class Affiliate(Base):
    __tablename__ = "affiliates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    leads: Mapped[list["Lead"]] = relationship(back_populates="affiliate")


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_created_at", "created_at"),
        Index("ix_leads_affiliate_created_at", "affiliate_id", "created_at"),
        Index(
            "ix_leads_dedup_window",
            "name",
            "phone",
            "offer_id",
            "affiliate_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), nullable=False)
    affiliate_id: Mapped[int] = mapped_column(ForeignKey("affiliates.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    offer: Mapped[Offer] = relationship(back_populates="leads")
    affiliate: Mapped[Affiliate] = relationship(back_populates="leads")


class ProcessedEvent(Base):
    __tablename__ = "processed_events"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_processed_events_event_id"),
        Index("ix_processed_events_processed_at", "processed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
