from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


from pydantic import BaseModel, EmailStr, Field

class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    full_name: str | None
    email: str
    is_verified: bool

    model_config = {
        "from_attributes": True
    }

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str | None = None

class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class ResetPasswordResponse(BaseModel):
    message: str

class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class ResetPasswordResponse(BaseModel):
    message: str

class ProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    phone: str | None
    bio: str | None
    skills: str | None
    experience_years: int | None
    education: str | None
    resume_url: str | None

    model_config = {
        "from_attributes": True
    }


class ProfileUpdateRequest(BaseModel):
    phone: str | None = Field(default=None, max_length=30)
    bio: str | None = Field(default=None, max_length=1000)
    skills: str | None = Field(default=None, max_length=2000)
    experience_years: int | None = Field(default=None, ge=0)
    education: str | None = Field(default=None, max_length=1000)
    resume_url: str | None = Field(default=None, max_length=500)