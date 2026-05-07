from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    kpk: str = Field(..., min_length=1, max_length=6)
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: "UserResponse"


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class ForgotPasswordRequest(BaseModel):
    kpk: str | None = Field(default=None, max_length=6)
    email: EmailStr | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class MessageResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    kpk: str
    name: str | None = None
    email: str | None = None
    supervisor: str | None = None
    join_date: str | None = None
    is_first_login: bool = False


TokenResponse.model_rebuild()
