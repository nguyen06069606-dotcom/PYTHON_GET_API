from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.config import settings

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)

def create_access_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": username, "iss": settings.jwt_issuer,
               "iat": now, "exp": now + timedelta(minutes=settings.jwt_access_token_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

