"""
Serveur Principal FastAPI
Système de Gestion des Rendez-vous Médicaux avec Chatbot IA
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os

# Charger les variables d'environnement
from dotenv import load_dotenv
load_dotenv()

# Imports locaux
from database import obtenir_session, initialiser_base_de_donnees
from models import Medecin, Utilisateur
from schemas import (
    MedecinReponse, RendezVousCreer,
    MessageChatRequete, MessageChatReponse,
    LoginRequete, UtilisateurAuthReponse,
    UtilisateurAdminReponse, RendezVousAdminReponse, RendezVousUpdateRequete,
    NotificationCreateRequete, NotificationReponse,
    MLPlaceholderRequete, MLPlaceholderReponse
)
from chatbot import ChatbotMedical
from session_auth import verifier_mot_de_passe, creer_session_token
from deps import get_current_user, require_roles
from models import RendezVous, Notification
from datetime import datetime

# ==================== Création de l'application ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise la base de données au démarrage"""
    initialiser_base_de_donnees()
    print("🚀 Serveur démarré avec succès!")
    print("📖 Documentation: http://localhost:8000/docs")
    print("💬 Application: http://localhost:8000/app")
    yield


app = FastAPI(
    title="🏥 Système de Rendez-vous Médicaux",
    description="""
    API pour la gestion des rendez-vous médicaux avec un chatbot intelligent.

    ## Fonctionnalités

    * 👨‍⚕️ **Médecins** - Liste et recherche de médecins
    * 📅 **Rendez-vous** - Réservation, consultation et annulation
    * 🤖 **Chatbot** - Assistant intelligent pour aider les patients
    * ⏰ **Disponibilités** - Vérification des créneaux horaires
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ==================== Configuration CORS ====================

app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Routes API ====================

@app.get("/", tags=["Général"])
async def racine():
    """Page d'accueil de l'API"""
    return {
        "message": "🏥 Bienvenue sur l'API de Gestion des Rendez-vous Médicaux",
        "version": "1.0.0",
        "documentation": "/docs",
        "application": "/app",
        "statut": "en ligne"
    }


# ==================== Routes Médecins ====================

@app.get("/api/medecins", response_model=List[MedecinReponse], tags=["Médecins"])
async def liste_medecins(
        specialite: Optional[str] = None,
        db: Session = Depends(obtenir_session)
):
    """
    Récupère la liste des médecins disponibles

    - **specialite**: Filtre optionnel par spécialité
    """
    requete = db.query(Medecin, Utilisateur).join(
        Utilisateur,
        Medecin.utilisateur_id == Utilisateur.id
    )

    if specialite:
        requete = requete.filter(Medecin.specialite.ilike(f"%{specialite}%"))

    medecins = requete.filter(Medecin.est_disponible == True).all()

    return [
        MedecinReponse(
            id=medecin.id,
            nom=utilisateur.nom,
            specialite=medecin.specialite,
            description=medecin.description,
            duree_consultation=medecin.duree_consultation
        )
        for medecin, utilisateur in medecins
    ]


@app.get("/api/medecins/{medecin_id}", response_model=MedecinReponse, tags=["Médecins"])
async def detail_medecin(
        medecin_id: int,
        db: Session = Depends(obtenir_session)
):
    """Récupère les détails d'un médecin spécifique"""
    resultat = db.query(Medecin, Utilisateur).join(
        Utilisateur,
        Medecin.utilisateur_id == Utilisateur.id
    ).filter(Medecin.id == medecin_id).first()

    if not resultat:
        raise HTTPException(status_code=404, detail="Médecin non trouvé")

    medecin, utilisateur = resultat
    return MedecinReponse(
        id=medecin.id,
        nom=utilisateur.nom,
        specialite=medecin.specialite,
        description=medecin.description,
        duree_consultation=medecin.duree_consultation
    )


# ==================== Routes Disponibilités ====================

@app.get("/api/medecins/{medecin_id}/disponibilites", tags=["Disponibilités"])
async def disponibilites_medecin(
        medecin_id: int,
        date: str,
        db: Session = Depends(obtenir_session)
):
    """
    Récupère les créneaux disponibles pour un médecin

    - **medecin_id**: ID du médecin
    - **date**: Date au format YYYY-MM-DD
    """
    chatbot = ChatbotMedical(db)
    return chatbot.obtenir_creneaux_disponibles(medecin_id, date)


# ==================== Routes Rendez-vous ====================

@app.post("/api/rendez-vous", tags=["Rendez-vous"])
async def creer_rendez_vous(
        rdv: RendezVousCreer,
        db: Session = Depends(obtenir_session)
):
    """
    Crée un nouveau rendez-vous

    Paramètres requis:
    - **medecin_id**: ID du médecin
    - **nom_patient**: Nom complet du patient
    - **telephone_patient**: Numéro de téléphone
    - **date**: Date au format YYYY-MM-DD
    - **heure**: Heure au format HH:MM
    """
    chatbot = ChatbotMedical(db)
    return chatbot.reserver_rendez_vous(
        medecin_id=rdv.medecin_id,
        nom_patient=rdv.nom_patient,
        telephone_patient=rdv.telephone_patient,
        date=rdv.date,
        heure=rdv.heure,
        motif=rdv.motif
    )


@app.get("/api/rendez-vous", tags=["Rendez-vous"])
async def mes_rendez_vous(
        telephone: str,
        db: Session = Depends(obtenir_session)
):
    """
    Récupère les rendez-vous d'un patient par son numéro de téléphone
    """
    chatbot = ChatbotMedical(db)
    return chatbot.consulter_mes_rendez_vous(telephone)


@app.delete("/api/rendez-vous/{rdv_id}", tags=["Rendez-vous"])
async def annuler_rdv(
        rdv_id: int,
        db: Session = Depends(obtenir_session)
):
    """Annule un rendez-vous existant"""
    chatbot = ChatbotMedical(db)
    return chatbot.annuler_rendez_vous(rdv_id)


# ==================== Routes Chatbot ====================

@app.post("/api/chat", response_model=MessageChatReponse, tags=["Chatbot"])
async def converser(
        requete: MessageChatRequete,
        db: Session = Depends(obtenir_session)
):
    """
    Endpoint de conversation avec le chatbot médical

    - **message**: Message de l'utilisateur
    - **historique_conversation**: Historique des messages précédents
    """
    chatbot = ChatbotMedical(db)

    reponse, nouvel_historique = await chatbot.discuter(
        requete.message,
        requete.historique_conversation
    )

    return MessageChatReponse(
        reponse=reponse,
        historique_conversation=nouvel_historique
    )


# ==================== Servir le Frontend ====================

# Chemin vers le dossier frontend
chemin_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
chemin_frontend = os.path.abspath(chemin_frontend)

# Vérifier si le dossier frontend existe
if os.path.exists(chemin_frontend):
    @app.get("/app", response_class=HTMLResponse, tags=["Application"])
    async def application_web():
        """Sert l'application web frontend"""
        fichier_index = os.path.join(chemin_frontend, "index.html")
        if os.path.exists(fichier_index):
            return FileResponse(fichier_index)
        raise HTTPException(status_code=404, detail="Frontend non trouvé")

    @app.get("/login.html", response_class=HTMLResponse, tags=["Application"])
    async def login_page():
        """Sert la page de connexion"""
        fichier = os.path.join(chemin_frontend, "login.html")
        if os.path.exists(fichier):
            return FileResponse(fichier)
        raise HTTPException(status_code=404, detail="Page non trouvée")

    @app.get("/dashboard-admin.html", response_class=HTMLResponse, tags=["Application"])
    async def dashboard_admin():
        """Sert le dashboard admin"""
        fichier = os.path.join(chemin_frontend, "dashboard-admin.html")
        if os.path.exists(fichier):
            return FileResponse(fichier)
        raise HTTPException(status_code=404, detail="Page non trouvée")

    @app.get("/dashboard-secretaire.html", response_class=HTMLResponse, tags=["Application"])
    async def dashboard_secretaire():
        """Sert le dashboard secrétaire"""
        fichier = os.path.join(chemin_frontend, "dashboard-secretaire.html")
        if os.path.exists(fichier):
            return FileResponse(fichier)
        raise HTTPException(status_code=404, detail="Page non trouvée")

    @app.get("/dashboard-medecin.html", response_class=HTMLResponse, tags=["Application"])
    async def dashboard_medecin():
        """Sert le dashboard médecin"""
        fichier = os.path.join(chemin_frontend, "dashboard-medecin.html")
        if os.path.exists(fichier):
            return FileResponse(fichier)
        raise HTTPException(status_code=404, detail="Page non trouvée")

    @app.get("/dashboard-patient.html", response_class=HTMLResponse, tags=["Application"])
    async def dashboard_patient():
        """Sert le dashboard patient"""
        fichier = os.path.join(chemin_frontend, "dashboard-patient.html")
        if os.path.exists(fichier):
            return FileResponse(fichier)
        raise HTTPException(status_code=404, detail="Page non trouvée")

    @app.get("/style.css", tags=["Application"])
    async def get_css():
        """Sert le fichier CSS"""
        fichier_css = os.path.join(chemin_frontend, "style.css")
        if os.path.exists(fichier_css):
            return FileResponse(fichier_css, media_type="text/css")
        raise HTTPException(status_code=404, detail="CSS non trouvé")

    @app.get("/dashboard.css", tags=["Application"])
    async def get_dashboard_css():
        """Sert le fichier CSS du dashboard"""
        fichier_css = os.path.join(chemin_frontend, "dashboard.css")
        if os.path.exists(fichier_css):
            return FileResponse(fichier_css, media_type="text/css")
        raise HTTPException(status_code=404, detail="CSS non trouvé")

    @app.get("/app.js", tags=["Application"])
    async def get_js():
        """Sert le fichier JavaScript"""
        fichier_js = os.path.join(chemin_frontend, "app.js")
        if os.path.exists(fichier_js):
            return FileResponse(fichier_js, media_type="application/javascript")
        raise HTTPException(status_code=404, detail="JS non trouvé")

    @app.get("/dashboard.js", tags=["Application"])
    async def get_dashboard_js():
        """Sert le fichier JavaScript du dashboard"""
        fichier_js = os.path.join(chemin_frontend, "dashboard.js")
        if os.path.exists(fichier_js):
            return FileResponse(fichier_js, media_type="application/javascript")
        raise HTTPException(status_code=404, detail="JS non trouvé")

    @app.get("/auth.js", tags=["Application"])
    async def get_auth_js():
        """Sert le fichier JavaScript d'authentification"""
        fichier_js = os.path.join(chemin_frontend, "auth.js")
        if os.path.exists(fichier_js):
            return FileResponse(fichier_js, media_type="application/javascript")
        raise HTTPException(status_code=404, detail="JS non trouvé")

    @app.get("/auth.css", tags=["Application"])
    async def get_auth_css():
        """Sert la feuille de style d'authentification"""
        fichier_css = os.path.join(chemin_frontend, "auth.css")
        if os.path.exists(fichier_css):
            return FileResponse(fichier_css, media_type="text/css")
        raise HTTPException(status_code=404, detail="CSS non trouvé")

    # Servir les fichiers statiques
    app.mount("/static", StaticFiles(directory=chemin_frontend), name="static")


# ==================== Auth ====================

@app.post("/api/auth/login", response_model=UtilisateurAuthReponse, tags=["Auth"])
async def login(requete: LoginRequete, response: Response, db: Session = Depends(obtenir_session)):
    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == requete.email).first()
    if not utilisateur or not utilisateur.mot_de_passe_hash:
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    if not verifier_mot_de_passe(requete.mot_de_passe, utilisateur.mot_de_passe_hash):
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    token = creer_session_token(utilisateur.id, utilisateur.role)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 12,
        path="/"
    )

    return UtilisateurAuthReponse(
        id=utilisateur.id,
        nom=utilisateur.nom,
        email=utilisateur.email,
        role=utilisateur.role,
        est_actif=utilisateur.est_actif
    )


@app.post("/api/auth/logout", tags=["Auth"])
async def logout(response: Response):
    response.delete_cookie("session_token", path="/")
    return {"succes": True}


@app.get("/api/auth/me", response_model=UtilisateurAuthReponse, tags=["Auth"])
async def me(utilisateur: Utilisateur = Depends(get_current_user)):
    return UtilisateurAuthReponse(
        id=utilisateur.id,
        nom=utilisateur.nom,
        email=utilisateur.email,
        role=utilisateur.role,
        est_actif=utilisateur.est_actif
    )

# ==================== Admin / Personnel ====================

@app.get("/api/admin/users", response_model=List[UtilisateurAdminReponse], tags=["Admin"])
async def lister_utilisateurs(
    db: Session = Depends(obtenir_session),
    _: Utilisateur = Depends(require_roles("admin"))
):
    utilisateurs = db.query(Utilisateur).order_by(Utilisateur.id.asc()).all()
    return [
        UtilisateurAdminReponse(
            id=u.id,
            nom=u.nom,
            email=u.email,
            telephone=u.telephone,
            role=u.role,
            est_actif=u.est_actif,
            date_creation=u.date_creation
        )
        for u in utilisateurs
    ]


@app.get("/api/admin/rendez-vous", response_model=List[RendezVousAdminReponse], tags=["Admin"])
async def lister_rendez_vous_admin(
    db: Session = Depends(obtenir_session),
    _: Utilisateur = Depends(require_roles("admin", "secretaire"))
):
    rendez_vous = db.query(RendezVous, Utilisateur, Medecin).join(
        Utilisateur, RendezVous.patient_id == Utilisateur.id
    ).join(
        Medecin, RendezVous.medecin_id == Medecin.id
    ).order_by(RendezVous.date_heure.asc()).all()

    resultats = []
    for rdv, patient, medecin in rendez_vous:
        medecin_user = db.query(Utilisateur).filter(Utilisateur.id == medecin.utilisateur_id).first()
        resultats.append(RendezVousAdminReponse(
            id=rdv.id,
            patient_id=patient.id,
            patient_nom=patient.nom,
            patient_telephone=patient.telephone,
            medecin_id=medecin.id,
            medecin_nom=medecin_user.nom if medecin_user else "Inconnu",
            date_heure=rdv.date_heure,
            statut=rdv.statut,
            motif=rdv.motif,
            notes=rdv.notes
        ))

    return resultats


@app.get("/api/medecin/rendez-vous", response_model=List[RendezVousAdminReponse], tags=["Médecin"])
async def lister_rendez_vous_medecin(
    db: Session = Depends(obtenir_session),
    utilisateur: Utilisateur = Depends(require_roles("medecin"))
):
    medecin = db.query(Medecin).filter(Medecin.utilisateur_id == utilisateur.id).first()
    if not medecin:
        raise HTTPException(status_code=404, detail="Médecin non trouvé")

    rendez_vous = db.query(RendezVous, Utilisateur).join(
        Utilisateur, RendezVous.patient_id == Utilisateur.id
    ).filter(
        RendezVous.medecin_id == medecin.id
    ).order_by(RendezVous.date_heure.asc()).all()

    resultats = []
    for rdv, patient in rendez_vous:
        resultats.append(RendezVousAdminReponse(
            id=rdv.id,
            patient_id=patient.id,
            patient_nom=patient.nom,
            patient_telephone=patient.telephone,
            medecin_id=medecin.id,
            medecin_nom=utilisateur.nom,
            date_heure=rdv.date_heure,
            statut=rdv.statut,
            motif=rdv.motif,
            notes=rdv.notes
        ))

    return resultats


@app.patch("/api/admin/rendez-vous/{rdv_id}", response_model=RendezVousAdminReponse, tags=["Admin"])
async def modifier_rendez_vous(
    rdv_id: int,
    requete: RendezVousUpdateRequete,
    db: Session = Depends(obtenir_session),
    _: Utilisateur = Depends(require_roles("admin", "secretaire"))
):
    rdv = db.query(RendezVous).filter(RendezVous.id == rdv_id).first()
    if not rdv:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")

    if requete.medecin_id is not None:
        rdv.medecin_id = requete.medecin_id
    if requete.date and requete.heure:
        try:
            rdv.date_heure = datetime.strptime(f"{requete.date} {requete.heure}", "%Y-%m-%d %H:%M")
        except ValueError:
            raise HTTPException(status_code=400, detail="Format date/heure invalide")
    if requete.statut is not None:
        rdv.statut = requete.statut
    if requete.motif is not None:
        rdv.motif = requete.motif
    if requete.notes is not None:
        rdv.notes = requete.notes

    db.commit()
    db.refresh(rdv)

    patient = db.query(Utilisateur).filter(Utilisateur.id == rdv.patient_id).first()
    medecin = db.query(Medecin).filter(Medecin.id == rdv.medecin_id).first()
    medecin_user = db.query(Utilisateur).filter(Utilisateur.id == medecin.utilisateur_id).first() if medecin else None

    return RendezVousAdminReponse(
        id=rdv.id,
        patient_id=patient.id if patient else 0,
        patient_nom=patient.nom if patient else "Inconnu",
        patient_telephone=patient.telephone if patient else None,
        medecin_id=medecin.id if medecin else 0,
        medecin_nom=medecin_user.nom if medecin_user else "Inconnu",
        date_heure=rdv.date_heure,
        statut=rdv.statut,
        motif=rdv.motif,
        notes=rdv.notes
    )


@app.post("/api/admin/notifications", response_model=NotificationReponse, tags=["Admin"])
async def creer_notification(
    requete: NotificationCreateRequete,
    db: Session = Depends(obtenir_session),
    _: Utilisateur = Depends(require_roles("admin", "secretaire"))
):
    notification = Notification(
        utilisateur_id=requete.utilisateur_id,
        sujet=requete.sujet,
        message=requete.message,
        canal=requete.canal or "placeholder",
        statut="en_attente"
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    return NotificationReponse(
        id=notification.id,
        utilisateur_id=notification.utilisateur_id,
        sujet=notification.sujet,
        message=notification.message,
        canal=notification.canal,
        statut=notification.statut,
        date_creation=notification.date_creation,
        date_envoi=notification.date_envoi
    )


@app.post("/api/admin/ml/placeholder", response_model=MLPlaceholderReponse, tags=["Admin"])
async def ml_placeholder(
    requete: MLPlaceholderRequete,
    _: Utilisateur = Depends(require_roles("admin", "secretaire"))
):
    suggestions = []
    if requete.specialite:
        suggestions.append({"specialite": requete.specialite, "score": 0.5})
    return MLPlaceholderReponse(
        succes=True,
        suggestions=suggestions,
        message="Placeholder ML: suggestions basées sur les entrées disponibles."
    )

# ==================== Point d'entrée ====================

if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*50)
    print("🏥 SYSTÈME DE RENDEZ-VOUS MÉDICAUX")
    print("="*50)
    print("\n🚀 Démarrage du serveur...")
    print("📖 Documentation API: http://localhost:8000/docs")
    print("💬 Application Web: http://localhost:8000/app")
    print("\nAppuyez sur Ctrl+C pour arrêter\n")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Rechargement automatique en développement
    )