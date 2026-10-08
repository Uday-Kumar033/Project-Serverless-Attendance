"""Password hashing (stdlib scrypt, no native deps) and JWT helpers."""
import base64
import hashlib
import hmac
import os
import time

import jwt

JWT_ALGO = "HS256"
TOKEN_TTL_SECONDS = 60 * 60 * 8  # 8 hours


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_b64, digest_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except ValueError:
        return False
    actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return hmac.compare_digest(actual, expected)


def create_token(user_id: str, role: str) -> str:
    now = int(time.time())
    payload = {"sub": user_id, "role": role, "iat": now, "exp": now + TOKEN_TTL_SECONDS}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGO)


def get_claims(event):
    """Return decoded JWT claims from the Authorization header, or None."""
    header = (event.get("headers") or {}).get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    try:
        return jwt.decode(header[7:], os.environ["JWT_SECRET"], algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        return None
