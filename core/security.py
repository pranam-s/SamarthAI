from datetime import datetime, timedelta, timezone
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from jose import jwt
from passlib.context import CryptContext

from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
CSRF_SALT = "samarth-csrf"


def _csrf_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt=CSRF_SALT)


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_csrf_token(subject: str | int) -> str:
    serializer = _csrf_serializer()
    return serializer.dumps({"sub": str(subject)})


def verify_csrf_token(token: str, subject: str | int, max_age_seconds: int = 60 * 60 * 2) -> bool:
    if not token:
        return False

    serializer = _csrf_serializer()
    try:
        data = serializer.loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return False

    return data.get("sub") == str(subject)