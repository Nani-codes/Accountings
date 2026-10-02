from pydantic import BaseModel, Field


class ExplainFindingOut(BaseModel):
    title: str
    description: str
    likely_reason: str
    recommended_action: str
    severity: str = Field(description="low|medium|high")


class ClientRequestOut(BaseModel):
    body: str


class WorkingPaperOut(BaseModel):
    narrative: str
    highlights: list[str] = Field(default_factory=list)
