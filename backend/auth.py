import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserSession


SESSION_DAYS = 30


def normalize_username(username: str) -> str:
    return str(username).strip().lower()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        method, salt, digest = stored_hash.split("$", 2)
        if method != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
        return secrets.compare_digest(candidate.hex(), digest)
    except Exception:
        return False


def create_user(db: Session, username: str, password: str) -> User:
    username = normalize_username(username)
    if len(username) < 3:
        raise ValueError("用户名至少需要 3 个字符")
    if len(password) < 6:
        raise ValueError("密码至少需要 6 个字符")
    if db.query(User).filter(User.username == username).first():
        raise ValueError("该用户名已存在")
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == normalize_username(username)).first()
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("用户名或密码错误")
    return user


def create_session(db: Session, user: User) -> UserSession:
    session = UserSession(
        user_id=user.id,
        token=secrets.token_urlsafe(48),
        expires_at=datetime.utcnow() + timedelta(days=SESSION_DAYS),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def revoke_session(db: Session, token: str):
    session = db.query(UserSession).filter(UserSession.token == token).first()
    if session:
        db.delete(session)
        db.commit()


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    token = authorization.split(" ", 1)[1].strip()
    session = db.query(UserSession).filter(UserSession.token == token).first()
    if not session or session.expires_at < datetime.utcnow():
        if session:
            db.delete(session)
            db.commit()
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="账号不存在，请重新登录")
    return user


def serialize_user(user: User) -> dict:
    return {"id": user.id, "username": user.username, "created_at": user.created_at}
