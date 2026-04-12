import base64
import hashlib
import html
import random
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import AuthCodePurpose, AuthVerificationCode, User
from schemas import (
    CaptchaResponse,
    PasswordResetConfirmRequest,
    PasswordResetSendCodeRequest,
    PasswordResetSendCodeResponse,
    Token,
    UserCreate,
    UserDetailResponse,
    UserLogin,
    UserResponse,
)
from security import create_access_token, get_current_user, hash_password, verify_password
from services.email_service import send_password_reset_code_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

_CAPTCHA_EXPIRE_SECONDS = 300
_PASSWORD_RESET_EXPIRE_MINUTES = 5
_PASSWORD_RESET_COOLDOWN_SECONDS = 30
_captcha_store: dict[str, dict] = {}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_auth_code_table(db: Session) -> None:
    # Safety net for environments without migrations.
    AuthVerificationCode.__table__.create(bind=db.get_bind(), checkfirst=True)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _cleanup_captcha_store() -> None:
    now = _now_utc()
    expired_ids = [cid for cid, item in _captcha_store.items() if item["expires_at"] <= now]
    for cid in expired_ids:
        _captcha_store.pop(cid, None)


def _generate_captcha_code(length: int = 5) -> str:
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "".join(random.choice(alphabet) for _ in range(length))


def _captcha_svg_base64(code: str) -> str:
    width, height = 150, 52
    letters = []
    for idx, char in enumerate(code):
        x = 16 + idx * 24 + random.randint(-2, 2)
        y = 34 + random.randint(-4, 4)
        rotate = random.randint(-18, 18)
        color = random.choice(["#1f2937", "#334155", "#0f172a", "#1e293b"])
        letters.append(
            f'<text x="{x}" y="{y}" fill="{color}" '
            f'font-size="24" font-family="Verdana" transform="rotate({rotate},{x},{y})">{html.escape(char)}</text>'
        )

    lines = []
    for _ in range(6):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        stroke = random.choice(["#94a3b8", "#64748b", "#cbd5e1"])
        lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="1.1"/>')

    dots = []
    for _ in range(30):
        cx, cy = random.randint(0, width), random.randint(0, height)
        fill = random.choice(["#94a3b8", "#64748b", "#cbd5e1"])
        dots.append(f'<circle cx="{cx}" cy="{cy}" r="0.9" fill="{fill}"/>')

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" fill="#f8fafc" rx="8" ry="8"/>'
        f'{"".join(lines)}{"".join(dots)}{"".join(letters)}'
        "</svg>"
    )
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"


def _verify_captcha(captcha_id: str, captcha_code: str) -> bool:
    _cleanup_captcha_store()
    item = _captcha_store.get(captcha_id)
    if not item:
        return False

    if item["expires_at"] <= _now_utc():
        _captcha_store.pop(captcha_id, None)
        return False

    matched = item["code"] == captcha_code.strip().upper()
    _captcha_store.pop(captcha_id, None)
    return matched


def _hash_plain_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@router.get("/captcha", response_model=CaptchaResponse)
async def get_captcha():
    """Generate an image captcha challenge"""
    _cleanup_captcha_store()
    captcha_id = secrets.token_urlsafe(18)
    code = _generate_captcha_code()
    _captcha_store[captcha_id] = {
        "code": code,
        "expires_at": _now_utc() + timedelta(seconds=_CAPTCHA_EXPIRE_SECONDS),
    }
    return {
        "captcha_id": captcha_id,
        "image_data": _captcha_svg_base64(code),
        "expires_in": _CAPTCHA_EXPIRE_SECONDS,
    }


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    if not _verify_captcha(user_data.captcha_id, user_data.captcha_code):
        raise HTTPException(status_code=400, detail="Captcha verification failed")

    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already registered")

    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user and return JWT token"""
    if not _verify_captcha(credentials.captcha_id, credentials.captcha_code):
        raise HTTPException(status_code=400, detail="Captcha verification failed")

    user = db.query(User).filter(
        (User.username == credentials.username) | (User.email == credentials.username)
    ).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.post("/password-reset/send-code", response_model=PasswordResetSendCodeResponse)
async def send_password_reset_code(
    payload: PasswordResetSendCodeRequest,
    db: Session = Depends(get_db),
):
    """Send password reset verification code via email"""
    _ensure_auth_code_table(db)

    if not _verify_captcha(payload.captcha_id, payload.captcha_code):
        raise HTTPException(status_code=400, detail="Captcha verification failed")

    account = payload.account.strip()
    user = db.query(User).filter((User.email == account) | (User.username == account)).first()
    if not user:
        return {"message": "If the email exists, a verification code has been sent."}

    now = _now_utc()
    latest_code = (
        db.query(AuthVerificationCode)
        .filter(
            AuthVerificationCode.email == user.email,
            AuthVerificationCode.purpose == AuthCodePurpose.PASSWORD_RESET,
        )
        .order_by(AuthVerificationCode.created_at.desc())
        .first()
    )

    latest_created_at = _as_utc(latest_code.created_at) if latest_code else None
    if latest_created_at and (now - latest_created_at).total_seconds() < _PASSWORD_RESET_COOLDOWN_SECONDS:
        raise HTTPException(status_code=429, detail="Please wait before requesting another code")

    code = f"{random.randint(0, 999999):06d}"
    db_code = AuthVerificationCode(
        email=user.email,
        code_hash=_hash_plain_code(code),
        purpose=AuthCodePurpose.PASSWORD_RESET,
        expires_at=now + timedelta(minutes=_PASSWORD_RESET_EXPIRE_MINUTES),
        used=False,
    )
    db.add(db_code)
    db.commit()

    delivery_result = {}
    try:
        delivery_result = send_password_reset_code_email(user.email, code)
    except Exception:
        # Keep reset flow available in non-production debugging scenarios.
        if settings.EMAIL_DEV_MODE:
            delivery_result = {"sent": False, "debug_code": code, "reason": "email_exception"}
        else:
            delivery_result = {"sent": False}

    response = {"message": "Verification code sent to your email."}
    debug_code = delivery_result.get("debug_code")
    if debug_code and settings.EMAIL_DEV_MODE:
        response["debug_code"] = debug_code
        response["message"] = "Development mode: verification code generated."
    return response


@router.post("/password-reset/confirm", response_model=PasswordResetSendCodeResponse)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    db: Session = Depends(get_db),
):
    """Confirm reset code and set a new password"""
    _ensure_auth_code_table(db)

    account = payload.account.strip()
    user = db.query(User).filter((User.email == account) | (User.username == account)).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    now = _now_utc()
    db_code = (
        db.query(AuthVerificationCode)
        .filter(
            AuthVerificationCode.email == user.email,
            AuthVerificationCode.purpose == AuthCodePurpose.PASSWORD_RESET,
            AuthVerificationCode.used == False,  # noqa: E712
        )
        .order_by(AuthVerificationCode.created_at.desc())
        .first()
    )
    if not db_code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    expires_at = _as_utc(db_code.expires_at)
    if not expires_at or expires_at < now:
        raise HTTPException(status_code=400, detail="Verification code has expired")
    if db_code.code_hash != _hash_plain_code(payload.code):
        raise HTTPException(status_code=400, detail="Invalid verification code")

    user.hashed_password = hash_password(payload.new_password)
    db_code.used = True

    (
        db.query(AuthVerificationCode)
        .filter(
            AuthVerificationCode.email == user.email,
            AuthVerificationCode.purpose == AuthCodePurpose.PASSWORD_RESET,
            AuthVerificationCode.id != db_code.id,
        )
        .update({"used": True}, synchronize_session=False)
    )

    db.commit()
    return {"message": "Password has been reset successfully."}


@router.get("/me", response_model=UserDetailResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user
