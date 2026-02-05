"""Session-based auth utilities using signed cookies."""
from datetime import timedelta, datetime
import os
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.context import CryptContext
from typing import Optional

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret")
COOKIE_NAME = "session_token"
COOKIE_MAX_AGE_SECONDS = 60 * 60 * 12  # 12 hours

serializer = URLSafeTimedSerializer(SECRET_KEY)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    mot_de_passe = mot_de_passe[:72]
    return pwd_context.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, mot_de_passe_hash: str) -> bool:
    # bcrypt supports up to 72 bytes; truncate to avoid errors
    mot_de_passe = mot_de_passe[:72]
    return pwd_context.verify(mot_de_passe, mot_de_passe_hash)


def creer_session_token(user_id: int, role: str) -> str:
    return serializer.dumps({"sub": user_id, "role": role})


def decoder_session_token(token: str) -> Optional[dict]:
    try:
        return serializer.loads(token, max_age=COOKIE_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
