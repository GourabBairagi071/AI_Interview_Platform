import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.modules.auth.model import PasswordResetToken, User
from app.modules.auth.schema import SignupRequest
from app.modules.auth.model import PasswordResetToken, User, UserProfile
from google.oauth2 import id_token
from google.auth.transport import requests
from app.core.config import settings

async def create_user(
    db: AsyncSession,
    data: SignupRequest,
) -> User:

    result = await db.execute(
        select(User).where(User.email == data.email)
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise ValueError("Email already registered")

    user = User(
        full_name=data.full_name,
        email=data.email,
        hashed_password=hash_password(data.password),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def authenticate_google_user(
    db: AsyncSession,
    credential: str,
) -> User:

    try:
        google_user = id_token.verify_oauth2_token(
            credential,
            requests.Request(),
            settings.google_client_id,
        )
    except ValueError as exc:
        raise ValueError("Invalid Google credential") from exc

    google_id = google_user.get("sub")
    email = google_user.get("email")
    full_name = google_user.get("name") or email

    if not google_id or not email:
        raise ValueError("Google account information is incomplete")

    result = await db.execute(
        select(User).where(User.email == email)
    )

    user = result.scalar_one_or_none()

    if user:
        if user.google_id and user.google_id != google_id:
            raise ValueError("Google account does not match this user")

        user.google_id = google_id
        user.is_verified = True

        await db.commit()
        await db.refresh(user)

        return user

    user = User(
        full_name=full_name,
        email=email,
        google_id=google_id,
        hashed_password=None,
        is_verified=True,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User | None:

    result = await db.execute(
        select(User).where(User.email == email)
    )

    user = result.scalar_one_or_none()

    if not user:
        return None

    if not user.is_active:
        return None

    if not user.hashed_password:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


async def create_password_reset_token(
    db: AsyncSession,
    email: str,
) -> str | None:

    result = await db.execute(
        select(User).where(User.email == email)
    )

    user = result.scalar_one_or_none()

    if not user:
        return None

    token = secrets.token_urlsafe(32)

    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )

    db.add(reset_token)
    await db.commit()

    return token

async def reset_password(
    db: AsyncSession,
    token: str,
    new_password: str,
) -> bool:

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == token,
            PasswordResetToken.used.is_(False),
        )
    )

    reset_token = result.scalar_one_or_none()

    if not reset_token:
        return False

    if reset_token.expires_at < datetime.now(timezone.utc):
        return False

    result = await db.execute(
        select(User).where(User.id == reset_token.user_id)
    )

    user = result.scalar_one_or_none()

    if not user:
        return False

    user.hashed_password = hash_password(new_password)
    reset_token.used = True

    await db.commit()

    return True

async def get_or_create_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> UserProfile:

    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )

    profile = result.scalar_one_or_none()

    if profile:
        return profile

    profile = UserProfile(user_id=user_id)

    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return profile

async def update_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    data,
) -> UserProfile:

    profile = await get_or_create_profile(db, user_id)

    profile.phone = data.phone
    profile.bio = data.bio
    profile.skills = data.skills
    profile.experience_years = data.experience_years
    profile.education = data.education
    profile.resume_url = data.resume_url

    await db.commit()
    await db.refresh(profile)

    return profile