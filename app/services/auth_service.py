from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.password_policy import validate_password_policy
from app.core.security import (
    create_access_token,
    create_random_token,
    hash_password,
    sha256_hash,
    verify_password,
)
from app.models.auth import AuthSession, AuthUser, PasswordResetToken
from app.models.employee import Employee
from app.schemas.auth import UserResponse
from app.services.email_service import send_password_reset_email

settings = get_settings()
MAX_FAILED_ATTEMPTS = 5


def get_employee_by_kpk(db: Session, kpk: str) -> Employee | None:
    return db.execute(select(Employee).where(Employee.KPK == kpk)).scalar_one_or_none()


def get_auth_user_by_kpk(db: Session, kpk: str) -> AuthUser | None:
    return db.execute(select(AuthUser).where(AuthUser.kpk == kpk)).scalar_one_or_none()


def build_user_response(employee: Employee, auth_user_existed_before_login: bool) -> UserResponse:
    return UserResponse(
        kpk=employee.KPK,
        name=employee.name,
        email=employee.email,
        supervisor=employee.supervisor,
        join_date=employee.join_date,
        is_first_login=not auth_user_existed_before_login,
    )


def login(db: Session, kpk: str, password: str, user_agent: str | None, ip_address: str | None):
    employee = get_employee_by_kpk(db, kpk)
    if not employee:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid KPK or password")

    if not employee.dob:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee DOB is missing")

    auth_user = get_auth_user_by_kpk(db, kpk)
    auth_user_existed_before_login = auth_user is not None

    if auth_user:
        if not auth_user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
        if auth_user.is_locked:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="User account is locked")

        if not verify_password(password, auth_user.password_hash):
            auth_user.failed_login_attempts += 1
            if auth_user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                auth_user.is_locked = True
            db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid KPK or password")
    else:
        # First successful login must use DOB as the default password.
        if password != employee.dob:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid KPK or password")
        auth_user = AuthUser(
            kpk=kpk,
            password_hash=hash_password(password),
            is_active=True,
            is_locked=False,
            failed_login_attempts=0,
        )
        db.add(auth_user)
        db.flush()

    now = datetime.utcnow()
    auth_user.failed_login_attempts = 0
    auth_user.last_login_at = now
    auth_user.updated_at = now

    refresh_token = create_random_token()
    refresh_token_hash = sha256_hash(refresh_token)
    session = AuthSession(
        auth_user_id=auth_user.id,
        refresh_token_hash=refresh_token_hash,
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    db.flush()

    access_token = create_access_token(subject=kpk, session_id=str(session.id))
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in_seconds": settings.access_token_expire_minutes * 60,
        "user": build_user_response(employee, auth_user_existed_before_login),
    }


def refresh_access_token(db: Session, refresh_token: str):
    token_hash = sha256_hash(refresh_token)
    session = db.execute(
        select(AuthSession).where(AuthSession.refresh_token_hash == token_hash)
    ).scalar_one_or_none()

    now = datetime.utcnow()
    if not session or session.is_revoked or session.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    auth_user = db.get(AuthUser, session.auth_user_id)
    if not auth_user or not auth_user.is_active or auth_user.is_locked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session")

    session.last_used_at = now
    db.commit()

    return {
        "access_token": create_access_token(subject=auth_user.kpk, session_id=str(session.id)),
        "expires_in_seconds": settings.access_token_expire_minutes * 60,
    }


def logout_current_session(db: Session, session_id: str):
    session = db.get(AuthSession, session_id)
    if session and not session.is_revoked:
        session.is_revoked = True
        session.revoked_at = datetime.utcnow()
        db.commit()


def request_password_reset(db: Session, kpk: str | None, email: str | None):
    if not kpk and not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="KPK or email is required")

    stmt = select(Employee)
    if kpk:
        stmt = stmt.where(Employee.KPK == kpk)
    else:
        stmt = stmt.where(Employee.email == email)

    employee = db.execute(stmt).scalar_one_or_none()

    # Avoid user enumeration. Always return success message, but only send if user exists.
    if not employee or not employee.email:
        return

    auth_user = get_auth_user_by_kpk(db, employee.KPK)
    if not auth_user:
        # Allows forgot password before prior login by creating auth_user with default DOB hash.
        if not employee.dob:
            return
        auth_user = AuthUser(kpk=employee.KPK, password_hash=hash_password(employee.dob))
        db.add(auth_user)
        db.flush()

    raw_token = create_random_token()
    reset_token = PasswordResetToken(
        auth_user_id=auth_user.id,
        token_hash=sha256_hash(raw_token),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.password_reset_token_expire_minutes),
    )
    db.add(reset_token)
    db.commit()

    reset_url = f"{settings.frontend_reset_password_url}?token={raw_token}"
    send_password_reset_email(employee.email, employee.name, reset_url)


def reset_password(db: Session, token: str, new_password: str):
    try:
        validate_password_policy(new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    token_hash = sha256_hash(token)
    reset_token = db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    ).scalar_one_or_none()

    now = datetime.utcnow()
    if not reset_token or reset_token.is_used or reset_token.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    auth_user = db.get(AuthUser, reset_token.auth_user_id)
    if not auth_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")

    auth_user.password_hash = hash_password(new_password)
    auth_user.password_changed_at = now
    auth_user.failed_login_attempts = 0
    auth_user.is_locked = False
    auth_user.updated_at = now
    reset_token.is_used = True
    reset_token.used_at = now

    # Revoke all sessions after reset password for safety.
    sessions = db.execute(select(AuthSession).where(AuthSession.auth_user_id == auth_user.id, AuthSession.is_revoked == False)).scalars().all()
    for session in sessions:
        session.is_revoked = True
        session.revoked_at = now

    db.commit()


def change_password(db: Session, auth_user: AuthUser, current_password: str, new_password: str):
    if not verify_password(current_password, auth_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    try:
        validate_password_policy(new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    now = datetime.utcnow()
    auth_user.password_hash = hash_password(new_password)
    auth_user.password_changed_at = now
    auth_user.updated_at = now
    db.commit()
