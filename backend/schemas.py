"""
Schémas Pydantic pour la validation des données API
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ==================== Schémas Utilisateur ====================

class UtilisateurBase(BaseModel):
    nom: str
    email: Optional[str] = None
    telephone: Optional[str] = None


class UtilisateurCreer(UtilisateurBase):
    mot_de_passe: Optional[str] = None
    role: str = "patient"


class UtilisateurReponse(UtilisateurBase):
    id: int
    role: str
    date_creation: datetime

    class Config:
        from_attributes = True


# ==================== Schémas Médecin ====================

class MedecinBase(BaseModel):
    specialite: str
    description: Optional[str] = None
    duree_consultation: int = 30


class MedecinReponse(BaseModel):
    id: int
    nom: str
    specialite: str
    description: Optional[str]
    duree_consultation: int

    class Config:
        from_attributes = True


# ==================== Schémas Rendez-vous ====================

class RendezVousCreer(BaseModel):
    medecin_id: int
    nom_patient: str
    telephone_patient: str
    date: str  # Format: YYYY-MM-DD
    heure: str  # Format: HH:MM
    motif: Optional[str] = None


class RendezVousReponse(BaseModel):
    id: int
    patient_id: int
    medecin_id: int
    date_heure: datetime
    statut: str
    motif: Optional[str]

    class Config:
        from_attributes = True


class CreneauDisponible(BaseModel):
    heure: str
    disponible: bool = True


class DisponibiliteReponse(BaseModel):
    succes: bool
    date: str
    nom_medecin: Optional[str] = None
    creneaux_disponibles: List[str] = []
    message: Optional[str] = None


# ==================== Schémas Chat ====================

class MessageChatRequete(BaseModel):
    message: str
    historique_conversation: Optional[List[dict]] = []
    session_id: Optional[str] = None


class MessageChatReponse(BaseModel):
    reponse: str
    historique_conversation: List[dict]


# ==================== Auth ====================

class LoginRequete(BaseModel):
    email: EmailStr
    mot_de_passe: str


class UtilisateurAuthReponse(BaseModel):
    id: int
    nom: str
    email: Optional[str] = None
    role: str
    est_actif: bool

    class Config:
        from_attributes = True


class TokenReponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UtilisateurAuthReponse


# ==================== Admin ====================

class UtilisateurAdminReponse(BaseModel):
    id: int
    nom: str
    email: Optional[str]
    telephone: Optional[str]
    role: str
    est_actif: bool
    date_creation: datetime

    class Config:
        from_attributes = True


class RendezVousAdminReponse(BaseModel):
    id: int
    patient_id: int
    patient_nom: str
    patient_telephone: Optional[str]
    medecin_id: int
    medecin_nom: str
    date_heure: datetime
    statut: str
    motif: Optional[str]
    notes: Optional[str]


class RendezVousUpdateRequete(BaseModel):
    medecin_id: Optional[int] = None
    date: Optional[str] = None  # YYYY-MM-DD
    heure: Optional[str] = None  # HH:MM
    statut: Optional[str] = None
    motif: Optional[str] = None
    notes: Optional[str] = None


# ==================== Notifications ====================

class NotificationCreateRequete(BaseModel):
    utilisateur_id: int
    sujet: str
    message: str
    canal: Optional[str] = "placeholder"


class NotificationReponse(BaseModel):
    id: int
    utilisateur_id: int
    sujet: str
    message: str
    canal: str
    statut: str
    date_creation: datetime
    date_envoi: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== ML Placeholder ====================

class MLPlaceholderRequete(BaseModel):
    contexte: Optional[str] = None
    specialite: Optional[str] = None
    date: Optional[str] = None


class MLPlaceholderReponse(BaseModel):
    succes: bool
    suggestions: List[dict] = []
    message: Optional[str] = None

