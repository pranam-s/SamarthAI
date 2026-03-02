from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from core.config import settings

ALGORITHM = "HS256"
CSRF_SALT = "samarth-csrf"


def _csrf_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt=CSRF_SALT)


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hash_bytes)


def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


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
