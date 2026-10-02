from pydantic import BaseModel


class PairingOut(BaseModel):
    code: str
    expires_at: str
    download_url: str | None = None


class TallyStatusOut(BaseModel):
    status: str
    device_label: str | None = None
    last_seen_at: str | None = None
    last_tally_ok_at: str | None = None


class ConnectorPairIn(BaseModel):
    code: str
    label: str | None = None


class ConnectorPairOut(BaseModel):
    device_id: str
    device_token: str
    ws_url: str
