from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import (
    limit_forgot_password_attempts,
    limit_login_attempts,
    limit_reset_password_attempts,
    limit_verify_otp_attempts,
)
from app.core.security import create_access_token
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.model import User
from app.modules.auth.schema import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    GoogleAuthRequest,
    LoginRequest,
    LoginResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SignupRequest,
    UserResponse,
    VerifyResetOTPRequest,
    VerifyResetOTPResponse,
)
from app.modules.auth.service import (
    authenticate_google_user,
    authenticate_user,
    create_and_send_password_reset_otp,
    create_user,
    get_or_create_profile,
    reset_password_with_token,
    update_profile,
    verify_password_reset_otp,
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
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(str(user.id))

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

    access_token = create_access_token(str(user.id))

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
    current_user: User = Depends(get_current_user),
):
    return current_user


# ============================================================
# FORGOT PASSWORD (REQUEST OTP)
# ============================================================

@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    dependencies=[Depends(limit_forgot_password_attempts)],
)
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else None
    success, message = await create_and_send_password_reset_otp(
        db=db,
        email=data.email,
        ip_address=client_ip,
    )

    if not success:
        # If rate limit / cooldown triggered
        if "60 seconds" in message:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=message,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return {"message": message}


# ============================================================
# VERIFY RESET OTP
# ============================================================

@router.post(
    "/verify-reset-otp",
    response_model=VerifyResetOTPResponse,
    dependencies=[Depends(limit_verify_otp_attempts)],
)
async def verify_reset_otp_route(
    data: VerifyResetOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    success, message, reset_token = await verify_password_reset_otp(
        db=db,
        email=data.email,
        otp=data.otp,
    )

    if not success or not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return {
        "message": message,
        "reset_token": reset_token,
    }


# ============================================================
# RESET PASSWORD
# ============================================================

@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    dependencies=[Depends(limit_reset_password_attempts)],
)
async def reset_password_route(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        token = data.effective_token
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    success, message = await reset_password_with_token(
        db=db,
        reset_token=token,
        new_password=data.new_password,
        confirm_password=data.confirm_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return {"message": message}


# ============================================================
# GET PROFILE
# ============================================================

@router.get(
    "/profile",
    response_model=ProfileResponse,
)
async def get_profile(
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await update_profile(
        db=db,
        user_id=current_user.id,
        data=data,
    )
    return profile