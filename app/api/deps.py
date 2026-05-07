from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.auth import AuthSession, AuthUser
from app.models.employee import Employee

bearer_scheme = HTTPBearer(auto_error=True)


class CurrentUserContext:
    def __init__(self, auth_user: AuthUser, employee: Employee, session_id: str):
        self.auth_user = auth_user
        self.employee = employee
        self.session_id = session_id


def get_current_user_context(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUserContext:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    kpk = payload.get("sub")
    session_id = payload.get("sid")
    if not kpk or not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    session = db.get(AuthSession, session_id)
    if not session or session.is_revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is no longer active")

    auth_user = db.execute(select(AuthUser).where(AuthUser.kpk == kpk)).scalar_one_or_none()
    if not auth_user or not auth_user.is_active or auth_user.is_locked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not active")

    employee = db.execute(select(Employee).where(Employee.KPK == kpk)).scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Employee not found")

    return CurrentUserContext(auth_user=auth_user, employee=employee, session_id=session_id)
