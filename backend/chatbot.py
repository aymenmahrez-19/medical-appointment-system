"""
Logique du Chatbot Médical Intelligent
Supporte le mode avec OpenAI API ou le mode simulation (sans API)
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session

from models import (
    Medecin, RendezVous, Utilisateur, HoraireMedecin,
    StatutRendezVous, RoleUtilisateur
)

# Vérifier si on utilise l'API OpenAI ou le mode simulation
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODE_SIMULATION = not OPENAI_API_KEY or OPENAI_API_KEY.startswith("your-")

if not MODE_SIMULATION:
    try:
        from openai import OpenAI
        client_openai = OpenAI(api_key=OPENAI_API_KEY)
    except ImportError:
        MODE_SIMULATION = True
        print("⚠️ Module OpenAI non installé. Mode simulation activé.")


# Prompt système pour le chatbot
PROMPT_SYSTEME = """Tu es un assistant médical intelligent pour une clinique médicale.

Tes responsabilités :
1. Aider les patients à prendre des rendez-vous
2. Afficher les médecins disponibles et leurs spécialités
3. Vérifier les créneaux horaires disponibles
4. Annuler ou modifier des rendez-vous
5. Répondre aux questions générales sur la clinique

Règles importantes :
- Sois toujours poli et professionnel
- Ne donne JAMAIS de diagnostic médical
- En cas d'urgence, dirige vers les urgences (15 ou 112)
- Réponds en français

Informations de la clinique :
- Horaires : 9h - 17h (Lundi au Vendredi)
- Adresse : 123 Avenue de la Santé, Paris
- Téléphone : 01 23 45 67 89

Quand un patient veut prendre rendez-vous :
1. Demande la spécialité souhaitée
2. Propose les médecins disponibles
3. Demande la date et l'heure préférées
4. Confirme le rendez-vous avec un résumé
"""


# Définition des fonctions pour l'API OpenAI
FONCTIONS_CHATBOT = [
    {
        "name": "obtenir_medecins",
        "description": "Obtenir la liste des médecins disponibles, avec filtrage optionnel par spécialité",
        "parameters": {
            "type": "object",
            "properties": {
                "specialite": {
                    "type": "string",
                    "description": "La spécialité recherchée (ex: Cardiologie, Dentiste, Pédiatrie)"
                }
            }
        }
    },
    {
        "name": "obtenir_creneaux_disponibles",
        "description": "Obtenir les créneaux horaires disponibles pour un médecin à une date donnée",
        "parameters": {
            "type": "object",
            "properties": {
                "medecin_id": {
                    "type": "integer",
                    "description": "L'identifiant du médecin"
                },
                "date": {
                    "type": "string",
                    "description": "La date au format YYYY-MM-DD"
                }
            },
            "required": ["medecin_id", "date"]
        }
    },
    {
        "name": "reserver_rendez_vous",
        "description": "Réserver un nouveau rendez-vous",
        "parameters": {
            "type": "object",
            "properties": {
                "medecin_id": {
                    "type": "integer",
                    "description": "L'identifiant du médecin"
                },
                "nom_patient": {
                    "type": "string",
                    "description": "Le nom complet du patient"
                },
                "telephone_patient": {
                    "type": "string",
                    "description": "Le numéro de téléphone du patient"
                },
                "date": {
                    "type": "string",
                    "description": "La date au format YYYY-MM-DD"
                },
                "heure": {
                    "type": "string",
                    "description": "L'heure au format HH:MM"
                },
                "motif": {
                    "type": "string",
                    "description": "Le motif de la consultation (optionnel)"
                }
            },
            "required": ["medecin_id", "nom_patient", "date", "heure"]
        }
    },
    {
        "name": "annuler_rendez_vous",
        "description": "Annuler un rendez-vous existant",
        "parameters": {
            "type": "object",
            "properties": {
                "rendez_vous_id": {
                    "type": "integer",
                    "description": "Le numéro du rendez-vous à annuler"
                }
            },
            "required": ["rendez_vous_id"]
        }
    },
    {
        "name": "consulter_mes_rendez_vous",
        "description": "Consulter les rendez-vous d'un patient",
        "parameters": {
            "type": "object",
            "properties": {
                "telephone_patient": {
                    "type": "string",
                    "description": "Le numéro de téléphone du patient"
                }
            },
            "required": ["telephone_patient"]
        }
    }
]


class ChatbotMedical:
    """
    Classe principale du chatbot médical
    """

    def __init__(self, db: Session):
        """
        Initialise le chatbot avec une session de base de données

        Args:
            db: Session SQLAlchemy pour accéder à la base de données
        """
        self.db = db

    # ==================== Fonctions de gestion des médecins ====================

    def obtenir_medecins(self, specialite: Optional[str] = None) -> dict:
        """
        Récupère la liste des médecins disponibles

        Args:
            specialite: Filtre optionnel par spécialité

        Returns:
            Dictionnaire avec la liste des médecins
        """
        # Requête avec jointure pour obtenir les noms
        requete = self.db.query(Medecin, Utilisateur).join(
            Utilisateur,
            Medecin.utilisateur_id == Utilisateur.id
        )

        # Filtrer par spécialité si spécifié
        if specialite:
            requete = requete.filter(
                Medecin.specialite.ilike(f"%{specialite}%")
            )

        # Filtrer les médecins disponibles
        medecins = requete.filter(Medecin.est_disponible == True).all()

        # Formater les résultats
        resultats = []
        for medecin, utilisateur in medecins:
            resultats.append({
                "id": medecin.id,
                "nom": utilisateur.nom,
                "specialite": medecin.specialite,
                "description": medecin.description,
                "duree_consultation": medecin.duree_consultation
            })

        return {
            "succes": True,
            "medecins": resultats,
            "nombre": len(resultats)
        }

    # ==================== Fonctions de gestion des créneaux ====================

    def obtenir_creneaux_disponibles(self, medecin_id: int, date: str) -> dict:
        """
        Récupère les créneaux horaires disponibles pour un médecin

        Args:
            medecin_id: ID du médecin
            date: Date au format YYYY-MM-DD

        Returns:
            Dictionnaire avec les créneaux disponibles
        """
        # Valider le format de la date
        try:
            date_cible = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {
                "succes": False,
                "erreur": "Format de date invalide. Utilisez YYYY-MM-DD"
            }

        # Vérifier que la date est dans le futur
        if date_cible.date() < datetime.now().date():
            return {
                "succes": False,
                "erreur": "Impossible de réserver dans le passé"
            }

        # Vérifier que le médecin existe
        medecin = self.db.query(Medecin).filter(Medecin.id == medecin_id).first()
        if not medecin:
            return {
                "succes": False,
                "erreur": "Médecin non trouvé"
            }

        # Obtenir le nom du médecin
        utilisateur = self.db.query(Utilisateur).filter(
            Utilisateur.id == medecin.utilisateur_id
        ).first()

        # Obtenir l'horaire du médecin pour ce jour
        jour_semaine = date_cible.weekday()
        horaire = self.db.query(HoraireMedecin).filter(
            HoraireMedecin.medecin_id == medecin_id,
            HoraireMedecin.jour_semaine == jour_semaine,
            HoraireMedecin.est_actif == True
        ).first()

        if not horaire:
            return {
                "succes": True,
                "creneaux_disponibles": [],
                "message": "Le médecin ne travaille pas ce jour-là"
            }

        # Générer tous les créneaux possibles
        heure_debut, minute_debut = map(int, horaire.heure_debut.split(":"))
        heure_fin, minute_fin = map(int, horaire.heure_fin.split(":"))

        duree = medecin.duree_consultation
        creneaux = []

        heure_actuelle = date_cible.replace(
            hour=heure_debut,
            minute=minute_debut,
            second=0,
            microsecond=0
        )
        heure_limite = date_cible.replace(
            hour=heure_fin,
            minute=minute_fin
        )

        # Obtenir les rendez-vous déjà réservés
        rendez_vous_existants = self.db.query(RendezVous).filter(
            RendezVous.medecin_id == medecin_id,
            RendezVous.date_heure >= date_cible,
            RendezVous.date_heure < date_cible + timedelta(days=1),
            RendezVous.statut.in_([
                StatutRendezVous.EN_ATTENTE.value,
                StatutRendezVous.CONFIRME.value
            ])
        ).all()

        heures_reservees = [rdv.date_heure for rdv in rendez_vous_existants]

        # Générer les créneaux disponibles
        maintenant = datetime.now()
        while heure_actuelle + timedelta(minutes=duree) <= heure_limite:
            # Vérifier si le créneau est dans le futur et non réservé
            if heure_actuelle > maintenant and heure_actuelle not in heures_reservees:
                creneaux.append(heure_actuelle.strftime("%H:%M"))
            heure_actuelle += timedelta(minutes=duree)

        return {
            "succes": True,
            "date": date,
            "nom_medecin": utilisateur.nom if utilisateur else "Inconnu",
            "creneaux_disponibles": creneaux
        }

    # ==================== Fonctions de réservation ====================

    def reserver_rendez_vous(
            self,
            medecin_id: int,
            nom_patient: str,
            date: str,
            heure: str,
            telephone_patient: str = None,
            motif: str = None
    ) -> dict:
        """
        Réserve un nouveau rendez-vous

        Args:
            medecin_id: ID du médecin
            nom_patient: Nom du patient
            date: Date au format YYYY-MM-DD
            heure: Heure au format HH:MM
            telephone_patient: Téléphone du patient
            motif: Motif de la consultation

        Returns:
            Dictionnaire avec les détails de la réservation
        """
        # Construire la date et l'heure du rendez-vous
        try:
            date_heure_rdv = datetime.strptime(f"{date} {heure}", "%Y-%m-%d %H:%M")
        except ValueError:
            return {
                "succes": False,
                "erreur": "Format de date ou d'heure invalide"
            }

        # Vérifier la disponibilité
        rdv_existant = self.db.query(RendezVous).filter(
            RendezVous.medecin_id == medecin_id,
            RendezVous.date_heure == date_heure_rdv,
            RendezVous.statut.in_([
                StatutRendezVous.EN_ATTENTE.value,
                StatutRendezVous.CONFIRME.value
            ])
        ).first()

        if rdv_existant:
            return {
                "succes": False,
                "erreur": "Ce créneau est déjà réservé. Veuillez choisir un autre horaire."
            }

        # Créer ou trouver le patient
        patient = None
        if telephone_patient:
            patient = self.db.query(Utilisateur).filter(
                Utilisateur.telephone == telephone_patient
            ).first()

        if not patient:
            patient = Utilisateur(
                nom=nom_patient,
                telephone=telephone_patient or "0000000000",
                role=RoleUtilisateur.PATIENT.value
            )
            self.db.add(patient)
            self.db.commit()
            self.db.refresh(patient)

        # Créer le rendez-vous
        nouveau_rdv = RendezVous(
            patient_id=patient.id,
            medecin_id=medecin_id,
            date_heure=date_heure_rdv,
            statut=StatutRendezVous.CONFIRME.value,
            motif=motif
        )

        self.db.add(nouveau_rdv)
        self.db.commit()
        self.db.refresh(nouveau_rdv)

        # Obtenir les informations du médecin
        medecin = self.db.query(Medecin, Utilisateur).join(
            Utilisateur,
            Medecin.utilisateur_id == Utilisateur.id
        ).filter(Medecin.id == medecin_id).first()

        return {
            "succes": True,
            "numero_rdv": f"RDV-{nouveau_rdv.id:04d}",
            "message": "Votre rendez-vous a été confirmé !",
            "details": {
                "Numéro": f"RDV-{nouveau_rdv.id:04d}",
                "Médecin": medecin[1].nom if medecin else "Inconnu",
                "Spécialité": medecin[0].specialite if medecin else "Inconnu",
                "Date": date,
                "Heure": heure,
                "Patient": nom_patient
            }
        }

    # ==================== Fonctions d'annulation ====================

    def annuler_rendez_vous(self, rendez_vous_id: int) -> dict:
        """
        Annule un rendez-vous existant

        Args:
            rendez_vous_id: ID du rendez-vous à annuler

        Returns:
            Dictionnaire avec le résultat de l'annulation
        """
        rdv = self.db.query(RendezVous).filter(
            RendezVous.id == rendez_vous_id
        ).first()

        if not rdv:
            return {
                "succes": False,
                "erreur": "Rendez-vous non trouvé"
            }

        if rdv.statut == StatutRendezVous.ANNULE.value:
            return {
                "succes": False,
                "erreur": "Ce rendez-vous est déjà annulé"
            }

        # Annuler le rendez-vous
        rdv.statut = StatutRendezVous.ANNULE.value
        self.db.commit()

        return {
            "succes": True,
            "message": f"Le rendez-vous RDV-{rendez_vous_id:04d} a été annulé avec succès"
        }

    # ==================== Fonctions de consultation ====================

    def consulter_mes_rendez_vous(self, telephone_patient: str) -> dict:
        """
        Récupère les rendez-vous d'un patient

        Args:
            telephone_patient: Numéro de téléphone du patient

        Returns:
            Dictionnaire avec la liste des rendez-vous
        """
        patient = self.db.query(Utilisateur).filter(
            Utilisateur.telephone == telephone_patient
        ).first()

        if not patient:
            return {
                "succes": False,
                "erreur": "Aucun rendez-vous trouvé avec ce numéro de téléphone"
            }

        # Obtenir les rendez-vous futurs
        rendez_vous = self.db.query(RendezVous, Medecin, Utilisateur).join(
            Medecin, RendezVous.medecin_id == Medecin.id
        ).join(
            Utilisateur, Medecin.utilisateur_id == Utilisateur.id
        ).filter(
            RendezVous.patient_id == patient.id,
            RendezVous.date_heure >= datetime.now()
        ).all()

        resultats = []
        for rdv, medecin, utilisateur_medecin in rendez_vous:
            resultats.append({
                "numero": f"RDV-{rdv.id:04d}",
                "medecin": utilisateur_medecin.nom,
                "specialite": medecin.specialite,
                "date": rdv.date_heure.strftime("%Y-%m-%d"),
                "heure": rdv.date_heure.strftime("%H:%M"),
                "statut": rdv.statut
            })

        return {
            "succes": True,
            "rendez_vous": resultats,
            "nombre": len(resultats)
        }

    # ==================== Traitement des fonctions ====================

    def traiter_appel_fonction(self, nom_fonction: str, arguments: dict) -> dict:
        """
        Exécute une fonction demandée par le chatbot

        Args:
            nom_fonction: Nom de la fonction à exécuter
            arguments: Arguments de la fonction

        Returns:
            Résultat de la fonction
        """
        fonctions = {
            "obtenir_medecins": self.obtenir_medecins,
            "obtenir_creneaux_disponibles": self.obtenir_creneaux_disponibles,
            "reserver_rendez_vous": self.reserver_rendez_vous,
            "annuler_rendez_vous": self.annuler_rendez_vous,
            "consulter_mes_rendez_vous": self.consulter_mes_rendez_vous
        }

        if nom_fonction in fonctions:
            return fonctions[nom_fonction](**arguments)

        return {"erreur": "Fonction inconnue"}

    # ==================== Mode simulation (sans OpenAI) ====================

    def obtenir_reponse_simulation(self, message_utilisateur: str) -> str:
        """
        Génère une réponse simulée sans utiliser l'API OpenAI
        Utile pour les tests et le développement

        Args:
            message_utilisateur: Message de l'utilisateur

        Returns:
            Réponse du chatbot
        """
        message = message_utilisateur.lower()

        # Salutations
        if any(mot in message for mot in ["bonjour", "salut", "hello", "bonsoir", "coucou"]):
            return """Bonjour ! 👋 Je suis l'assistant médical intelligent de la clinique.

Je peux vous aider à :
• 📋 Voir la liste des médecins
• 📅 Prendre un rendez-vous
• ⏰ Vérifier les disponibilités
• ❌ Annuler un rendez-vous

Comment puis-je vous aider aujourd'hui ?"""

        # Demande de médecins
        elif any(mot in message for mot in ["médecin", "medecin", "docteur", "liste", "spécialité", "specialite"]):
            medecins = self.obtenir_medecins()
            if medecins["medecins"]:
                reponse = "👨‍⚕️ **Voici nos médecins disponibles :**\n\n"
                for doc in medecins["medecins"]:
                    reponse += f"• **{doc['nom']}** - {doc['specialite']}\n"
                    reponse += f"  _{doc['description']}_\n"
                    reponse += f"  Durée consultation : {doc['duree_consultation']} min\n\n"
                reponse += "Souhaitez-vous prendre rendez-vous avec l'un d'entre eux ?"
                return reponse
            return "Aucun médecin disponible pour le moment."

        # Demande de rendez-vous
        elif any(mot in message for mot in ["rendez-vous", "rdv", "réserver", "reserver", "prendre"]):
            return """Pour prendre un rendez-vous, j'ai besoin des informations suivantes :

1️⃣ **Spécialité souhaitée** (Médecine Générale, Cardiologie, Dentiste, Pédiatrie)
2️⃣ **Date préférée** (ex: demain, lundi prochain)
3️⃣ **Heure préférée** (ex: 10h00, 14h30)
4️⃣ **Votre nom complet**
5️⃣ **Votre numéro de téléphone**

Quelle spécialité souhaitez-vous consulter ?"""

        # Disponibilités
        elif any(mot in message for mot in ["disponible", "créneau", "creneau", "horaire", "libre"]):
            demain = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            creneaux = self.obtenir_creneaux_disponibles(1, demain)
            if creneaux.get("creneaux_disponibles"):
                return f"""⏰ **Créneaux disponibles pour le {demain} :**

{chr(10).join(['• ' + c for c in creneaux['creneaux_disponibles'][:8]])}

Quel créneau vous conviendrait ?"""
            return "Pas de créneaux disponibles pour cette date. Essayez une autre date."

        # Annulation
        elif any(mot in message for mot in ["annuler", "annulation", "supprimer"]):
            return """Pour annuler votre rendez-vous, j'ai besoin de :

• **Numéro du rendez-vous** (ex: RDV-0001)

ou

• **Votre numéro de téléphone** pour retrouver vos rendez-vous

Pouvez-vous me fournir l'une de ces informations ?"""

        # Remerciements
        elif any(mot in message for mot in ["merci", "thanks", "au revoir", "bye"]):
            return """Je vous en prie ! 😊

N'hésitez pas à revenir si vous avez d'autres questions.

🏥 **Informations pratiques :**
• Adresse : 123 Avenue de la Santé, Paris
• Téléphone : 01 23 45 67 89
• Horaires : Lundi-Vendredi, 9h-17h

Bonne journée et prenez soin de vous ! 🌟"""

        # Urgence
        elif any(mot in message for mot in ["urgence", "urgent", "grave", "douleur forte"]):
            return """🚨 **ATTENTION - URGENCE MÉDICALE**

Si vous êtes en situation d'urgence :
• Appelez le **15** (SAMU)
• Ou le **112** (Urgences européennes)

Si ce n'est pas une urgence vitale mais que vous avez besoin d'une consultation rapide, je peux vous aider à trouver le prochain créneau disponible.

Décrivez-moi votre situation."""

        # Réponse par défaut
        else:
            return """Je suis là pour vous aider avec vos rendez-vous médicaux. 🏥

Voici ce que je peux faire :
• **"médecins"** - Voir la liste des médecins
• **"rendez-vous"** - Prendre un rendez-vous
• **"disponibilités"** - Voir les créneaux libres
• **"annuler"** - Annuler un rendez-vous

Comment puis-je vous aider ?"""

    # ==================== Fonction principale de chat ====================

    async def discuter(
            self,
            message_utilisateur: str,
            historique: List[dict] = None
    ) -> Tuple[str, List[dict]]:
        """
        Fonction principale de conversation

        Args:
            message_utilisateur: Message de l'utilisateur
            historique: Historique de la conversation

        Returns:
            Tuple (réponse, nouvel_historique)
        """
        if historique is None:
            historique = []

        # Mode simulation (sans API OpenAI)
        if MODE_SIMULATION:
            reponse = self.obtenir_reponse_simulation(message_utilisateur)
            nouvel_historique = historique + [
                {"role": "user", "content": message_utilisateur},
                {"role": "assistant", "content": reponse}
            ]
            return reponse, nouvel_historique

        # Mode avec API OpenAI
        messages = [{"role": "system", "content": PROMPT_SYSTEME}]
        messages.extend(historique)
        messages.append({"role": "user", "content": message_utilisateur})

        try:
            # Appel à l'API OpenAI
            reponse_api = client_openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                functions=FONCTIONS_CHATBOT,
                function_call="auto",
                temperature=0.7
            )

            message_assistant = reponse_api.choices[0].message

            # Vérifier si une fonction doit être appelée
            if message_assistant.function_call:
                nom_fonction = message_assistant.function_call.name
                arguments = json.loads(message_assistant.function_call.arguments)

                # Exécuter la fonction
                resultat_fonction = self.traiter_appel_fonction(nom_fonction, arguments)

                # Ajouter le résultat à la conversation
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "function_call": {
                        "name": nom_fonction,
                        "arguments": message_assistant.function_call.arguments
                    }
                })
                messages.append({
                    "role": "function",
                    "name": nom_fonction,
                    "content": json.dumps(resultat_fonction, ensure_ascii=False)
                })

                # Obtenir la réponse finale
                reponse_finale = client_openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7
                )

                reponse_texte = reponse_finale.choices[0].message.content
            else:
                reponse_texte = message_assistant.content

            # Mettre à jour l'historique
            nouvel_historique = historique + [
                {"role": "user", "content": message_utilisateur},
                {"role": "assistant", "content": reponse_texte}
            ]

            return reponse_texte, nouvel_historique

        except Exception as e:
            erreur = f"Désolé, une erreur s'est produite : {str(e)}"
            return erreur, historique