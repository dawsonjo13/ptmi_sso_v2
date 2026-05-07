from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUserContext, get_current_user_context
from app.db.session import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RefreshResponse,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    change_password,
    login,
    logout_current_session,
    refresh_access_token,
    request_password_reset,
    reset_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login_endpoint(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    result = login(
        db=db,
        kpk=payload.kpk,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return result


@router.post("/refresh", response_model=RefreshResponse)
def refresh_endpoint(payload: RefreshRequest, db: Session = Depends(get_db)):
    return refresh_access_token(db, payload.refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout_endpoint(ctx: CurrentUserContext = Depends(get_current_user_context), db: Session = Depends(get_db)):
    logout_current_session(db, ctx.session_id)
    return MessageResponse(message="Logged out successfully")


@router.post("/forgot-password", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
def forgot_password_endpoint(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    request_password_reset(db, payload.kpk, str(payload.email) if payload.email else None)
    return MessageResponse(message="If the account exists, a password reset email has been sent")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password_endpoint(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    reset_password(db, payload.token, payload.new_password)
    return MessageResponse(message="Password has been reset successfully")


@router.post("/change-password", response_model=MessageResponse)
def change_password_endpoint(
    payload: ChangePasswordRequest,
    ctx: CurrentUserContext = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    change_password(db, ctx.auth_user, payload.current_password, payload.new_password)
    return MessageResponse(message="Password has been changed successfully")


@router.get("/me", response_model=UserResponse)
def me_endpoint(ctx: CurrentUserContext = Depends(get_current_user_context)):
    return UserResponse(
        kpk=ctx.employee.KPK,
        name=ctx.employee.name,
        email=ctx.employee.email,
        supervisor=ctx.employee.supervisor,
        join_date=ctx.employee.join_date,
        is_first_login=False,
    )
