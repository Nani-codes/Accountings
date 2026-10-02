from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str
    firm_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: str


class OrganizationOut(BaseModel):
    id: str
    name: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    organization: OrganizationOut


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
