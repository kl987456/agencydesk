import hashlib
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import Depends, Header, HTTPException, Request
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from .db import get_db
from .models import Identity, Membership, Role

pwd = CryptContext(schemes=["argon2"], deprecated="auto")
_sessions: dict[str, tuple[str, float]] = {}
_rate: dict[str, list[float]] = {}


@dataclass
class AuthContext:
    identity: Identity
    membership: Membership
    agency_id: str


def hash_password(value: str) -> str:
    return pwd.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    return pwd.verify(value, hashed)


def create_session(identity_id: str, agency_id: str) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = (f"{identity_id}:{agency_id}", time.time() + 60 * 60 * 8)
    return token


def revoke_session(token: str) -> None:
    _sessions.pop(token, None)


def rate_limit(key: str, limit: int = 10, window: int = 60) -> None:
    now = time.time()
    recent = [stamp for stamp in _rate.get(key, []) if now - stamp < window]
    if len(recent) >= limit:
        raise HTTPException(429, "Too many attempts; try again shortly")
    recent.append(now)
    _rate[key] = recent


def get_auth_context(request: Request, db: Session = Depends(get_db), authorization: str | None = Header(default=None)) -> AuthContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required")
    stored = _sessions.get(authorization[7:])
    if not stored or stored[1] < time.time():
        raise HTTPException(401, "Session expired")
    identity_id, agency_id = (UUID(value) for value in stored[0].split(":", 1))
    membership = db.scalar(select(Membership).options(joinedload(Membership.identity)).where(Membership.identity_id == identity_id, Membership.agency_id == agency_id, Membership.active.is_(True)))
    if not membership:
        raise HTTPException(403, "Membership inactive")
    db.info["agency_id"] = agency_id
    request.state.auth = AuthContext(membership.identity, membership, agency_id)
    return request.state.auth


def role_required(*roles: Role):
    def dependency(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if ctx.membership.role not in roles:
            raise HTTPException(403, "Insufficient role")
        return ctx
    return dependency
