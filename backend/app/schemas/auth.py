from pydantic import BaseModel, EmailStr, Field


class BootstrapOwnerRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)
    device_name: str | None = Field(default=None, max_length=120)


class InviteRegisterRequest(BaseModel):
    invite_code: str = Field(min_length=4, max_length=96)
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)
    device_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    username_or_email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)
    device_name: str | None = Field(default=None, max_length=120)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
