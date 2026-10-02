from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


# Prefer JSONB on Postgres; fall back to JSON for SQLite tests if ever used.
JsonType = JSON().with_variant(JSONB(), "postgresql")
UuidType = UUID(as_uuid=True)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UuidType, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    users: Mapped[list[User]] = relationship(back_populates="organization")
    clients: Mapped[list[Client]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UuidType, primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    google_sub: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization: Mapped[Organization] = relationship(back_populates="users")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UuidType, primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    services: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=lambda: ["GST"])
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization: Mapped[Organization] = relationship(back_populates="clients")
    documents: Mapped[list[ClientDocument]] = relationship(back_populates="client")
    runs: Mapped[list[ReconciliationRun]] = relationship(back_populates="client")


class ClientDocument(Base):
    __tablename__ = "client_documents"

    id: Mapped[uuid.UUID] = mapped_column(UuidType, primary_key=True, default=_uuid)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UuidType, ForeignKey("reconciliation_runs.id", ondelete="SET NULL"), nullable=True
    )
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    parsed_stats: Mapped[Optional[dict[str, Any]]] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    client: Mapped[Client] = relationship(back_populates="documents")
    run: Mapped[Optional[ReconciliationRun]] = relationship(back_populates="documents")


class ColumnMappingProfile(Base):
    __tablename__ = "column_mapping_profiles"
    __table_args__ = (
        UniqueConstraint("client_id", "doc_type", name="uq_mapping_client_doc_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UuidType, primary_key=True, default=_uuid)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    template_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UuidType, primary_key=True, default=_uuid)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JsonType, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    client: Mapped[Client] = relationship(back_populates="runs")
    documents: Mapped[list[ClientDocument]] = relationship(back_populates="run")
    invoices: Mapped[list[Invoice]] = relationship(back_populates="run")
    results: Mapped[list[ReconciliationResult]] = relationship(back_populates="run")
    findings: Mapped[list[AiFinding]] = relationship(back_populates="run")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UuidType, primary_key=True, default=_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)  # purchase|gstr2b|sales
    invoice_number: Mapped[str] = mapped_column(String(128), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    supplier_gstin: Mapped[str] = mapped_column(String(15), nullable=False)
    recipient_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    taxable_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    igst: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    cgst: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    sgst: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    cess: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    raw: Mapped[Optional[dict[str, Any]]] = mapped_column(JsonType, nullable=True)

    run: Mapped[ReconciliationRun] = relationship(back_populates="invoices")


class ReconciliationResult(Base):
    __tablename__ = "reconciliation_results"

    id: Mapped[uuid.UUID] = mapped_column(UuidType, primary_key=True, default=_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), nullable=False
    )
    purchase_invoice_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    gstr_invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UuidType, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )
    match_status: Mapped[str] = mapped_column(String(64), nullable=False)
    match_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    difference_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    difference_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    run: Mapped[ReconciliationRun] = relationship(back_populates="results")


class AiFinding(Base):
    __tablename__ = "ai_findings"

    id: Mapped[uuid.UUID] = mapped_column(UuidType, primary_key=True, default=_uuid)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped[ReconciliationRun] = relationship(back_populates="findings")


class ClientRequest(Base):
    __tablename__ = "client_requests"

    id: Mapped[uuid.UUID] = mapped_column(UuidType, primary_key=True, default=_uuid)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), nullable=False
    )
    finding_ids: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    response_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UuidType, primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UuidType, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UuidType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UuidType, nullable=True)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

