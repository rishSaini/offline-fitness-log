from datetime import datetime, timedelta, timezone
import os

from jose import jwt
from passlib.context import CryptContext

# ----- Password hashing -----
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ----- JWT -----
ALGORITHM = "HS256"

def _secret_key() -> str:
    # use env var if set, otherwise dev fallback
    return os.getenv("JWT_SECRET", "dev-secret-change-me")

def create_access_token(subject: str, expires_minutes: int = 60 * 24 * 7) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, _secret_key(), algorithm=ALGORITHM)
