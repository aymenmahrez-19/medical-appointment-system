"""
Modèles de base de données SQLAlchemy
Définit la structure des tables pour le système de rendez-vous médicaux
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

# Base pour tous les modèles
Base = declarative_base()


class RoleUtilisateur(enum.Enum):
    """Rôles possibles pour les utilisateurs"""
    PATIENT = "patient"
    MEDECIN = "medecin"
    SECRETAIRE = "secretaire"
    ADMIN = "admin"


class StatutRendezVous(enum.Enum):
    """Statuts possibles pour les rendez-vous"""
    EN_ATTENTE = "en_attente"
    CONFIRME = "confirme"
    ANNULE = "annule"
    TERMINE = "termine"


class Utilisateur(Base):
    """
    Table des utilisateurs (patients, médecins, secrétaires)
    """
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True)
    telephone = Column(String(20))
    mot_de_passe_hash = Column(String(255))
    role = Column(String(20), default=RoleUtilisateur.PATIENT.value)
    est_actif = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    # Relations
    rendez_vous_patient = relationship(
        "RendezVous",
        back_populates="patient",
        foreign_keys="RendezVous.patient_id"
    )
    notifications = relationship("Notification", back_populates="utilisateur")


class Medecin(Base):
    """
    Table des médecins avec leurs spécialités
    """
    __tablename__ = "medecins"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"))
    specialite = Column(String(100), nullable=False)
    description = Column(String(500))
    duree_consultation = Column(Integer, default=30)  # en minutes
    est_disponible = Column(Boolean, default=True)

    # Relations
    rendez_vous = relationship("RendezVous", back_populates="medecin")
    horaires = relationship("HoraireMedecin", back_populates="medecin")


class HoraireMedecin(Base):
    """
    Table des horaires de travail des médecins
    """
    __tablename__ = "horaires_medecins"

    id = Column(Integer, primary_key=True, index=True)
    medecin_id = Column(Integer, ForeignKey("medecins.id"))
    jour_semaine = Column(Integer)  # 0=Lundi, 6=Dimanche
    heure_debut = Column(String(5))  # "09:00"
    heure_fin = Column(String(5))    # "17:00"
    est_actif = Column(Boolean, default=True)

    # Relations
    medecin = relationship("Medecin", back_populates="horaires")


class RendezVous(Base):
    """
    Table des rendez-vous médicaux
    """
    __tablename__ = "rendez_vous"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("utilisateurs.id"))
    medecin_id = Column(Integer, ForeignKey("medecins.id"))
    date_heure = Column(DateTime, nullable=False)
    statut = Column(String(20), default=StatutRendezVous.EN_ATTENTE.value)
    motif = Column(String(500))
    notes = Column(Text)
    date_creation = Column(DateTime, default=datetime.utcnow)

    # Relations
    patient = relationship("Utilisateur", back_populates="rendez_vous_patient")
    medecin = relationship("Medecin", back_populates="rendez_vous")


class MessageChat(Base):
    """
    Table pour stocker l'historique des conversations du chatbot
    """
    __tablename__ = "messages_chat"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True)
    role = Column(String(20))  # user, assistant
    contenu = Column(Text)
    date_creation = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    """Table pour stocker les notifications (placeholder)."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"))
    canal = Column(String(20), default="placeholder")
    sujet = Column(String(200))
    message = Column(Text)
    statut = Column(String(20), default="en_attente")
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_envoi = Column(DateTime)

    utilisateur = relationship("Utilisateur", back_populates="notifications")

