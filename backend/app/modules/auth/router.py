from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User
from app.modules.auth.schema import (
    SignupRequest,
    UserResponse,
    LoginRequest,
    LoginResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    GoogleAuthRequest,
)
from app.modules.auth.service import (
    authenticate_user,
    create_password_reset_token,
    create_user,
    get_or_create_profile,
    reset_password,
    update_profile,
    authenticate_google_user,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ============================================================
# REGISTER
# ============================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: SignupRequest,
    db: AsyncSession = Depends(get_db),
):

    try:

        user = await create_user(
            db=db,
            data=data,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return user


from app.core.rate_limit import limit_login_attempts

# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(limit_login_attempts)],
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):

    user = await authenticate_user(
        db=db,
        email=data.email,
        password=data.password,
    )

    if not user:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    access_token = create_access_token(
    str(user.id)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }
# ============================================================
# GOOGLE LOGIN / REGISTER
# ============================================================

@router.post(
    "/google",
    response_model=LoginResponse,
)
async def google_auth(
    data: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
):

    try:
        user = await authenticate_google_user(
            db=db,
            credential=data.credential,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    access_token = create_access_token(
        str(user.id)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


# ============================================================
# CURRENT USER
# ============================================================

@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: User = Depends(
        get_current_user
    ),
):

    return current_user


# ============================================================
# FORGOT PASSWORD
# ============================================================

@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):

    token = await create_password_reset_token(
        db=db,
        email=data.email,
    )

    return {
        "message": (
            "If the email is registered, "
            "a password reset token has been generated."
        ),
        "reset_token": token,
    }


# ============================================================
# RESET PASSWORD
# ============================================================

@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
)
async def reset_password_route(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):

    success = await reset_password(
        db=db,
        token=data.token,
        new_password=data.new_password,
    )

    if not success:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired reset token"
            ),
        )

    return {
        "message": (
            "Password reset successfully"
        ),
    }


# ============================================================
# GET PROFILE
# ============================================================

@router.get(
    "/profile",
    response_model=ProfileResponse,
)
async def get_profile(
    current_user: User = Depends(
        get_current_user
    ),
    db: AsyncSession = Depends(get_db),
):

    profile = await get_or_create_profile(
        db=db,
        user_id=current_user.id,
    )

    return profile


# ============================================================
# UPDATE PROFILE
# ============================================================

@router.put(
    "/profile",
    response_model=ProfileResponse,
)
async def update_user_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: AsyncSession = Depends(get_db),
):

    profile = await update_profile(
        db=db,
        user_id=current_user.id,
        data=data,
    )

    return profile