from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core import config


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str = Field(min_length=1, max_length=config.PASSWORD_MAX_BYTES)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > config.PASSWORD_MAX_BYTES:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class SignupRequest(LoginRequest):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if len(value) < config.PASSWORD_MIN_LENGTH:
            raise ValueError("Use a password or passphrase of at least 12 characters")
        return value

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name must not be blank")
        return value.strip()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    name: str | None
    preferred_buffer_days: int


class SignupResponse(BaseModel):
    user_id: UUID
    token: str


class LoginResponse(BaseModel):
    token: str
    user: UserResponse
