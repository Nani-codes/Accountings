from pydantic import BaseModel, Field


class ClientCreate(BaseModel):
    name: str = Field(min_length=1)
    gstin: str | None = None
    services: list[str] = Field(default_factory=lambda: ["GST"])


class ClientOut(BaseModel):
    id: str
    name: str
    gstin: str | None
    services: list[str]
    gst_review_status: str | None = None


class ActivityItem(BaseModel):
    client_id: str
    client_name: str
    label: str
    run_id: str | None = None


class DashboardOut(BaseModel):
    clients: int
    active_gst_reviews: int
    exceptions: int
    client_responses_pending: int
    recent_activity: list[ActivityItem]
