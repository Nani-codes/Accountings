"""initial

Revision ID: 83671094f842
Revises:
Create Date: 2026-10-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "83671094f842"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid = postgresql.UUID(as_uuid=True)
jsonb = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("google_sub", sa.String(255), nullable=True, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "clients",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("gstin", sa.String(15), nullable=True),
        sa.Column("services", jsonb, nullable=False, server_default=sa.text("'[\"GST\"]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "reconciliation_runs",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("client_id", uuid, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", uuid, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("summary", jsonb, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "client_documents",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("client_id", uuid, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", uuid, sa.ForeignKey("reconciliation_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("parsed_stats", jsonb, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "column_mapping_profiles",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("client_id", uuid, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("mapping", jsonb, nullable=False),
        sa.Column("template_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("client_id", "doc_type", name="uq_mapping_client_doc_type"),
    )
    op.create_table(
        "invoices",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("run_id", uuid, sa.ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("invoice_number", sa.String(128), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("supplier_gstin", sa.String(15), nullable=False),
        sa.Column("recipient_gstin", sa.String(15), nullable=True),
        sa.Column("taxable_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("igst", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("cgst", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("sgst", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("cess", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        sa.Column("raw", jsonb, nullable=True),
    )
    op.create_table(
        "reconciliation_results",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("run_id", uuid, sa.ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purchase_invoice_id", uuid, sa.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gstr_invoice_id", uuid, sa.ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("match_status", sa.String(64), nullable=False),
        sa.Column("match_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("difference_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("difference_type", sa.String(64), nullable=True),
    )
    op.create_table(
        "ai_findings",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("client_id", uuid, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", uuid, sa.ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "client_requests",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("client_id", uuid, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", uuid, sa.ForeignKey("reconciliation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finding_ids", jsonb, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("response_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", uuid, nullable=True),
        sa.Column("payload", jsonb, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("client_requests")
    op.drop_table("ai_findings")
    op.drop_table("reconciliation_results")
    op.drop_table("invoices")
    op.drop_table("column_mapping_profiles")
    op.drop_table("client_documents")
    op.drop_table("reconciliation_runs")
    op.drop_table("clients")
    op.drop_table("users")
    op.drop_table("organizations")
