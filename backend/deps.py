"""FastAPI dependencies for session cookie auth and role checks."""

from fastapi import Depends, HTTPException, Cookie
from sqlalchemy.orm import Session

from database import obtenir_session
from models import Utilisateur
from session_auth import decoder_session_token


def get_current_user(
    session_token: str | None = Cookie(default=None, alias="session_token"),
    db: Session = Depends(obtenir_session)
) -> Utilisateur:
    if not session_token:
        raise HTTPException(status_code=401, detail="Session manquante")

    payload = decoder_session_token(session_token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Session invalide")

    user = db.query(Utilisateur).filter(Utilisateur.id == payload["sub"]).first()
    if not user or not user.est_actif:
        raise HTTPException(status_code=401, detail="Utilisateur non autorisé")

    return user


def require_roles(*roles: str):
    def _checker(user: Utilisateur = Depends(get_current_user)) -> Utilisateur:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Accès refusé")
        return user

    return _checker
