from app.models import (
    AiFinding,
    AuditLog,
    Client,
    ClientDocument,
    ClientRequest,
    ColumnMappingProfile,
    Invoice,
    Organization,
    ReconciliationResult,
    ReconciliationRun,
    User,
)


def test_model_tablename():
    assert Organization.__tablename__ == "organizations"
    assert User.__tablename__ == "users"
    assert Client.__tablename__ == "clients"
    assert ClientDocument.__tablename__ == "client_documents"
    assert ColumnMappingProfile.__tablename__ == "column_mapping_profiles"
    assert ReconciliationRun.__tablename__ == "reconciliation_runs"
    assert Invoice.__tablename__ == "invoices"
    assert ReconciliationResult.__tablename__ == "reconciliation_results"
    assert AiFinding.__tablename__ == "ai_findings"
    assert ClientRequest.__tablename__ == "client_requests"
    assert AuditLog.__tablename__ == "audit_logs"
