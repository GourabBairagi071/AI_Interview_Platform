import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from google.auth.transport import requests
from google.oauth2 import id_token
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.email import send_password_reset_otp_email
from app.core.security import hash_password, verify_password
from app.modules.auth.model import PasswordResetOTP, PasswordResetToken, User, UserProfile
from app.modules.auth.schema import SignupRequest


def hash_otp(otp: str) -> str:
    """Hash the 6-digit OTP using HMAC-SHA256 with the application secret key."""
    return hmac.new(settings.secret_key.encode("utf-8"), otp.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_otp_hash(otp: str, stored_hash: str) -> bool:
    """Constant-time verification of candidate OTP against stored hash."""
    computed_hash = hash_otp(otp)
    return hmac.compare_digest(stored_hash, computed_hash)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate that password meets platform security requirements:
    - Minimum 8 characters, maximum 128 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password cannot exceed 128 characters."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    special_chars = set(r"""!@#$%^&*(),.?":{}|<>\-_=+[]/~`';""")
    if not any(c in special_chars or not c.isalnum() for c in password):
        return False, "Password must contain at least one special character."
    return True, ""


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


# ============================================================
# FORGOT PASSWORD & OTP SERVICE
# ============================================================

async def create_and_send_password_reset_otp(
    db: AsyncSession,
    email: str,
    ip_address: str | None = None,
) -> tuple[bool, str]:
    """
    Generate and send a 6-digit OTP to the requested email.
    Enforces:
    - Account enumeration prevention (returns same message regardless of whether user exists)
    - 60-second resend cooldown for active requests
    - Cryptographically secure 6-digit OTP generation
    - Invalidation of previous active OTPs
    - Secure hashing before DB storage
    - 10-minute expiry
    """
    normalized_email = email.strip().lower()
    generic_success_msg = "If an account exists for this email, a password reset OTP has been sent."

    result = await db.execute(
        select(User).where(func.lower(User.email) == normalized_email)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        # Prevent account enumeration: return standard success message
        return True, generic_success_msg

    # Check resend cooldown (minimum 60 seconds between requests)
    now = datetime.now(timezone.utc)
    recent_query = await db.execute(
        select(PasswordResetOTP)
        .where(PasswordResetOTP.user_id == user.id)
        .order_by(PasswordResetOTP.created_at.desc())
        .limit(1)
    )
    recent_otp = recent_query.scalar_one_or_none()

    if recent_otp and (now - recent_otp.created_at).total_seconds() < 60:
        return False, "Please wait 60 seconds before requesting another OTP."

    # Invalidate previous unverified OTPs for this user
    await db.execute(
        update(PasswordResetOTP)
        .where(
            PasswordResetOTP.user_id == user.id,
            PasswordResetOTP.used_at.is_(None),
            PasswordResetOTP.verified_at.is_(None),
        )
        .values(used_at=now)
    )

    # Generate cryptographically secure 6-digit OTP
    otp = f"{secrets.randbelow(900000) + 100000:06d}"
    otp_hash = hash_otp(otp)
    expires_at = now + timedelta(minutes=10)

    otp_record = PasswordResetOTP(
        user_id=user.id,
        email=normalized_email,
        otp_hash=otp_hash,
        expires_at=expires_at,
        attempts=0,
        max_attempts=5,
        ip_address=ip_address,
    )
    db.add(otp_record)
    await db.commit()

    # Dispatch email through configured service / fallback simulation
    await send_password_reset_otp_email(to_email=user.email, otp=otp)

    return True, generic_success_msg


async def verify_password_reset_otp(
    db: AsyncSession,
    email: str,
    otp: str,
) -> tuple[bool, str, str | None]:
    """
    Verify the 6-digit OTP for the given email.
    Enforces:
    - 6-digit numeric pattern
    - Expiration check (10 minutes)
    - Max attempts check (5 attempts)
    - Replay/reuse prevention
    - Single-use consumption
    - Returns a short-lived, cryptographically secure reset token on success
    """
    normalized_email = email.strip().lower()

    if not re.match(r"^\d{6}$", otp.strip()):
        return False, "OTP must be a 6-digit numeric code.", None

    result = await db.execute(
        select(User).where(func.lower(User.email) == normalized_email)
    )
    user = result.scalar_one_or_none()

    if not user:
        return False, "Invalid or expired OTP.", None

    now = datetime.now(timezone.utc)

    # Fetch latest unverified OTP record
    otp_query = await db.execute(
        select(PasswordResetOTP)
        .where(
            PasswordResetOTP.user_id == user.id,
            PasswordResetOTP.verified_at.is_(None),
        )
        .order_by(PasswordResetOTP.created_at.desc())
        .limit(1)
    )
    otp_record = otp_query.scalar_one_or_none()

    if not otp_record:
        return False, "Invalid or expired OTP.", None

    if otp_record.used_at is not None or otp_record.attempts >= otp_record.max_attempts:
        return False, "Maximum verification attempts exceeded. Please request a new OTP.", None

    if otp_record.expires_at < now:
        otp_record.used_at = now
        await db.commit()
        return False, "OTP has expired. Please request a new one.", None

    # Increment attempts
    otp_record.attempts += 1

    # Verify hash
    if not verify_otp_hash(otp.strip(), otp_record.otp_hash):
        if otp_record.attempts >= otp_record.max_attempts:
            otp_record.used_at = now
            await db.commit()
            return False, "Invalid OTP. Maximum attempts exceeded. Please request a new OTP.", None
        await db.commit()
        remaining = otp_record.max_attempts - otp_record.attempts
        return False, f"Invalid OTP. {remaining} attempt(s) remaining.", None


    # Success: mark verified and generate single-use reset authorization token
    otp_record.verified_at = now
    reset_token = secrets.token_urlsafe(32)

    token_record = PasswordResetToken(
        user_id=user.id,
        token=reset_token,
        expires_at=now + timedelta(minutes=15),
        used=False,
    )
    db.add(token_record)
    await db.commit()

    return True, "OTP verified successfully.", reset_token


async def reset_password_with_token(
    db: AsyncSession,
    reset_token: str,
    new_password: str,
    confirm_password: str | None = None,
) -> tuple[bool, str]:
    """
    Reset user password using single-use authorization token.
    Enforces:
    - Token validity and expiration
    - Single-use consumption
    - Password confirmation match
    - Password strength policy
    - Invalidation of outstanding OTPs and reset tokens
    - Preservation of existing roles and permissions
    """
    if confirm_password is not None and new_password != confirm_password:
        return False, "Passwords do not match."

    is_strong, err_msg = validate_password_strength(new_password)
    if not is_strong:
        return False, err_msg

    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == reset_token,
            PasswordResetToken.used.is_(False),
        )
    )
    token_record = result.scalar_one_or_none()

    if not token_record:
        return False, "Invalid or expired reset token."

    if token_record.expires_at < now:
        token_record.used = True
        await db.commit()
        return False, "Reset token has expired."

    user_result = await db.execute(
        select(User).where(User.id == token_record.user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user or not user.is_active:
        return False, "User account not found or inactive."

    # Update password and mark token used
    user.hashed_password = hash_password(new_password)
    user.updated_at = now
    token_record.used = True

    # Invalidate any other active reset tokens for this user
    await db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used.is_(False),
        )
        .values(used=True)
    )

    # Invalidate all remaining OTPs for this user
    await db.execute(
        update(PasswordResetOTP)
        .where(
            PasswordResetOTP.user_id == user.id,
            PasswordResetOTP.used_at.is_(None),
        )
        .values(used_at=now)
    )

    await db.commit()
    return True, "Password reset successfully."


# Backward compatibility helpers
async def create_password_reset_token(
    db: AsyncSession,
    email: str,
) -> str | None:
    ok, _ = await create_and_send_password_reset_otp(db, email)
    return None


async def reset_password(
    db: AsyncSession,
    token: str,
    new_password: str,
) -> bool:
    ok, _ = await reset_password_with_token(db, token, new_password)
    return ok


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