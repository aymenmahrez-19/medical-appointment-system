"""
Configuration et initialisation de la base de donn��es
Inclut les données de démonstration
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import (
    Base, Utilisateur, Medecin, HoraireMedecin,
    RendezVous, RoleUtilisateur, StatutRendezVous
)
from datetime import datetime, timedelta
import os
from passlib.context import CryptContext
from session_auth import hacher_mot_de_passe

# URL de la base de données (SQLite par défaut)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./medical_appointments.db")

# Création du moteur de base de données
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Nécessaire pour SQLite
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def initialiser_base_de_donnees():
    """
    Crée les tables et ajoute des données de démonstration
    """
    # Créer toutes les tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Vérifier si les données existent déjà
    if db.query(Medecin).count() > 0:
        # Assurer la présence d'un admin et d'un secrétaire
        mot_de_passe_admin = hacher_mot_de_passe("admin123")
        admin = db.query(Utilisateur).filter(Utilisateur.email == "admin@clinique.fr").first()
        if not admin:
            db.add(Utilisateur(
                nom="Admin Clinique",
                email="admin@clinique.fr",
                telephone="0600000000",
                role=RoleUtilisateur.ADMIN.value,
                mot_de_passe_hash=mot_de_passe_admin
            ))
        secretaire = db.query(Utilisateur).filter(Utilisateur.email == "secretariat@clinique.fr").first()
        if not secretaire:
            db.add(Utilisateur(
                nom="Secrétaire Clinique",
                email="secretariat@clinique.fr",
                telephone="0600000001",
                role=RoleUtilisateur.SECRETAIRE.value,
                mot_de_passe_hash=mot_de_passe_admin
            ))
        db.commit()

        print("✅ Base de données déjà initialisée")
        db.close()
        return

    print("🔄 Initialisation de la base de données...")

    # ========== Création des utilisateurs ==========
    mot_de_passe_admin = hacher_mot_de_passe("admin123")
    mot_de_passe_personnel = hacher_mot_de_passe("medecin123")

    utilisateurs = [
        Utilisateur(
            nom="Admin Clinique",
            email="admin@clinique.fr",
            telephone="0600000000",
            role=RoleUtilisateur.ADMIN.value,
            mot_de_passe_hash=mot_de_passe_admin
        ),
        Utilisateur(
            nom="Secrétaire Clinique",
            email="secretariat@clinique.fr",
            telephone="0600000001",
            role=RoleUtilisateur.SECRETAIRE.value,
            mot_de_passe_hash=mot_de_passe_admin
        ),
        Utilisateur(
            nom="Dr. Martin Dupont",
            email="martin.dupont@clinique.fr",
            telephone="0612345001",
            role="medecin",
            mot_de_passe_hash=mot_de_passe_personnel
        ),
        Utilisateur(
            nom="Dr. Sophie Bernard",
            email="sophie.bernard@clinique.fr",
            telephone="0612345002",
            role="medecin",
            mot_de_passe_hash=mot_de_passe_personnel
        ),
        Utilisateur(
            nom="Dr. Pierre Lambert",
            email="pierre.lambert@clinique.fr",
            telephone="0612345003",
            role="medecin",
            mot_de_passe_hash=mot_de_passe_personnel
        ),
        Utilisateur(
            nom="Dr. Marie Leroy",
            email="marie.leroy@clinique.fr",
            telephone="0612345004",
            role="medecin",
            mot_de_passe_hash=mot_de_passe_personnel
        ),
        Utilisateur(
            nom="Jean Patient",
            email="patient@test.fr",
            telephone="0698765432",
            role="patient",
            mot_de_passe_hash=hacher_mot_de_passe("patient123")
        ),
    ]

    for utilisateur in utilisateurs:
        db.add(utilisateur)
    db.commit()

    # ========== Création des médecins ==========
    medecins = [
        Medecin(
            utilisateur_id=3,
            specialite="Médecine Générale",
            description="Médecin généraliste avec 15 ans d'expérience",
            duree_consultation=20
        ),
        Medecin(
            utilisateur_id=4,
            specialite="Cardiologie",
            description="Spécialiste des maladies cardiovasculaires",
            duree_consultation=30
        ),
        Medecin(
            utilisateur_id=5,
            specialite="Dentiste",
            description="Chirurgien-dentiste spécialisé en orthodontie",
            duree_consultation=45
        ),
        Medecin(
            utilisateur_id=6,
            specialite="Pédiatrie",
            description="Spécialiste de la santé des enfants",
            duree_consultation=25
        ),
    ]

    for medecin in medecins:
        db.add(medecin)
    db.commit()

    # ========== Création des horaires ==========
    jours_semaine = {
        0: "Lundi",
        1: "Mardi",
        2: "Mercredi",
        3: "Jeudi",
        4: "Vendredi"
    }

    for medecin_id in [1, 2, 3, 4]:
        for jour in range(5):  # Lundi à Vendredi
            horaire = HoraireMedecin(
                medecin_id=medecin_id,
                jour_semaine=jour,
                heure_debut="09:00",
                heure_fin="17:00"
            )
            db.add(horaire)
    db.commit()

    # ========== Création de rendez-vous de démonstration ==========
    demain = datetime.now() + timedelta(days=1)

    rendez_vous_demo = [
        RendezVous(
            patient_id=7,
            medecin_id=1,
            date_heure=demain.replace(hour=10, minute=0, second=0, microsecond=0),
            statut=StatutRendezVous.CONFIRME.value,
            motif="Consultation générale"
        ),
    ]

    for rdv in rendez_vous_demo:
        db.add(rdv)
    db.commit()

    db.close()
    print("✅ Base de données initialisée avec succès!")
    print("   - 4 médecins créés")
    print("   - 1 patient de test créé")
    print("   - Horaires configurés (Lundi-Vendredi, 9h-17h)")


def obtenir_session():
    """
    Générateur de session pour l'injection de dépendances FastAPI
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()