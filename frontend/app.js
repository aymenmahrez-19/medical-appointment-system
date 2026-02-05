/**
 * Application JavaScript pour le Système de Rendez-vous Médicaux
 * Gère le frontend, le chatbot et les interactions utilisateur
 */

// ==================== Configuration ====================
const CONFIG = {
    API_URL: 'http://localhost:8000',
    DELAI_TOAST: 4000,
    DELAI_TYPING: 1500
};

// ==================== État de l'Application ====================
let state = {
    medecins: [],
    historiqueChat: [],
    chatOuvert: false,
    enChargement: false,
    utilisateur: null
};

// ==================== Initialisation ====================
document.addEventListener('DOMContentLoaded', () => {
    initialiserApplication();
});

function initialiserApplication() {
    console.log('🏥 Initialisation de l\'application...');

    // Charger les médecins
    chargerMedecins();

    // Configurer les événements
    configurerEvenements();

    // Définir la date minimale (aujourd'hui)
    definirDateMinimale();

    // Initialiser l'authentification
    initialiserAuth();

    console.log('✅ Application initialisée');
}

function configurerEvenements() {
    // Formulaire de réservation
    const form = document.getElementById('formReservation');
    if (form) {
        form.addEventListener('submit', gererSoumissionFormulaire);
    }

    // Changement de spécialité
    const selectSpecialite = document.getElementById('specialite');
    if (selectSpecialite) {
        selectSpecialite.addEventListener('change', filtrerMedecins);
    }

    // Changement de médecin
    const selectMedecin = document.getElementById('medecin');
    if (selectMedecin) {
        selectMedecin.addEventListener('change', chargerCreneaux);
    }

    // Changement de date
    const inputDate = document.getElementById('date');
    if (inputDate) {
        inputDate.addEventListener('change', chargerCreneaux);
    }
}

function definirDateMinimale() {
    const inputDate = document.getElementById('date');
    if (inputDate) {
        const aujourdhui = new Date().toISOString().split('T')[0];
        inputDate.setAttribute('min', aujourdhui);
    }
}

// ==================== Gestion des Médecins ====================
async function chargerMedecins() {
    const container = document.getElementById('medecinsList');

    try {
        const reponse = await fetch(`${CONFIG.API_URL}/api/medecins`);

        if (!reponse.ok) {
            throw new Error('Erreur lors du chargement des médecins');
        }

        state.medecins = await reponse.json();
        afficherMedecins(state.medecins);

    } catch (erreur) {
        console.error('Erreur:', erreur);

        // Données de démonstration si le serveur n'est pas disponible
        state.medecins = [
            {
                id: 1,
                nom: "Dr. Martin Dupont",
                specialite: "Médecine Générale",
                description: "Médecin généraliste avec 15 ans d'expérience",
                duree_consultation: 20
            },
            {
                id: 2,
                nom: "Dr. Sophie Bernard",
                specialite: "Cardiologie",
                description: "Spécialiste des maladies cardiovasculaires",
                duree_consultation: 30
            },
            {
                id: 3,
                nom: "Dr. Pierre Lambert",
                specialite: "Dentiste",
                description: "Chirurgien-dentiste spécialisé en orthodontie",
                duree_consultation: 45
            },
            {
                id: 4,
                nom: "Dr. Marie Leroy",
                specialite: "Pédiatrie",
                description: "Spécialiste de la santé des enfants",
                duree_consultation: 25
            }
        ];

        afficherMedecins(state.medecins);
        afficherToast('Mode démo - Serveur non disponible', 'info');
    }
}

function afficherMedecins(medecins) {
    const container = document.getElementById('medecinsList');

    if (!container) return;

    if (medecins.length === 0) {
        container.innerHTML = `
            <div class="loading">
                <p>Aucun médecin disponible pour le moment</p>
            </div>
        `;
        return;
    }

    const icones = {
        'Médecine Générale': '👨‍⚕️',
        'Cardiologie': '❤️',
        'Dentiste': '🦷',
        'Pédiatrie': '👶'
    };

    container.innerHTML = medecins.map(medecin => `
        <div class="medecin-card">
            <div class="medecin-avatar">
                ${icones[medecin.specialite] || '👨‍⚕️'}
            </div>
            <h3>${medecin.nom}</h3>
            <span class="medecin-specialite">${medecin.specialite}</span>
            <p class="medecin-description">${medecin.description || ''}</p>
            <span class="medecin-duree">⏱️ ${medecin.duree_consultation} min / consultation</span>
            <button class="btn btn-primary btn-small" onclick="reserverAvecMedecin(${medecin.id})">
                📅 Prendre RDV
            </button>
        </div>
    `).join('');
}

function filtrerMedecins() {
    const specialite = document.getElementById('specialite').value;
    const selectMedecin = document.getElementById('medecin');

    // Réinitialiser
    selectMedecin.innerHTML = '<option value="">Choisir un médecin...</option>';
    selectMedecin.disabled = true;
    document.getElementById('heure').innerHTML = '<option value="">Choisir une heure...</option>';
    document.getElementById('heure').disabled = true;

    if (!specialite) return;

    // Filtrer les médecins par spécialité
    const medecinsFiltres = state.medecins.filter(m => m.specialite === specialite);

    if (medecinsFiltres.length > 0) {
        medecinsFiltres.forEach(medecin => {
            const option = document.createElement('option');
            option.value = medecin.id;
            option.textContent = medecin.nom;
            selectMedecin.appendChild(option);
        });
        selectMedecin.disabled = false;
    }
}

function reserverAvecMedecin(medecinId) {
    const medecin = state.medecins.find(m => m.id === medecinId);

    if (medecin) {
        // Aller à la section réservation
        document.getElementById('reservation').scrollIntoView({ behavior: 'smooth' });

        // Remplir les champs
        const selectSpecialite = document.getElementById('specialite');
        selectSpecialite.value = medecin.specialite;

        // Déclencher le changement
        filtrerMedecins();

        // Sélectionner le médecin
        setTimeout(() => {
            document.getElementById('medecin').value = medecinId;
        }, 100);
    }
}

// ==================== Gestion des Créneaux ====================
async function chargerCreneaux() {
    const medecinId = document.getElementById('medecin').value;
    const date = document.getElementById('date').value;
    const selectHeure = document.getElementById('heure');

    // Réinitialiser
    selectHeure.innerHTML = '<option value="">Choisir une heure...</option>';
    selectHeure.disabled = true;

    if (!medecinId || !date) return;

    try {
        const reponse = await fetch(
            `${CONFIG.API_URL}/api/medecins/${medecinId}/disponibilites?date=${date}`
        );

        if (!reponse.ok) {
            throw new Error('Erreur lors du chargement des créneaux');
        }

        const data = await reponse.json();

        if (data.creneaux_disponibles && data.creneaux_disponibles.length > 0) {
            data.creneaux_disponibles.forEach(creneau => {
                const option = document.createElement('option');
                option.value = creneau;
                option.textContent = creneau;
                selectHeure.appendChild(option);
            });
            selectHeure.disabled = false;
        } else {
            selectHeure.innerHTML = '<option value="">Aucun créneau disponible</option>';
            afficherToast(data.message || 'Aucun créneau disponible pour cette date', 'info');
        }

    } catch (erreur) {
        console.error('Erreur:', erreur);

        // Créneaux de démonstration
        const creneauxDemo = ['09:00', '09:30', '10:00', '10:30', '11:00', '14:00', '14:30', '15:00', '15:30', '16:00'];
        creneauxDemo.forEach(creneau => {
            const option = document.createElement('option');
            option.value = creneau;
            option.textContent = creneau;
            selectHeure.appendChild(option);
        });
        selectHeure.disabled = false;
    }
}

// ==================== Gestion du Formulaire ====================
async function gererSoumissionFormulaire(event) {
    event.preventDefault();

    const donnees = {
        medecin_id: parseInt(document.getElementById('medecin').value),
        nom_patient: document.getElementById('nomPatient').value,
        telephone_patient: document.getElementById('telephone').value,
        date: document.getElementById('date').value,
        heure: document.getElementById('heure').value,
        motif: document.getElementById('motif').value || null
    };

    // Validation
    if (!donnees.medecin_id || !donnees.nom_patient || !donnees.date || !donnees.heure) {
        afficherToast('Veuillez remplir tous les champs obligatoires', 'error');
        return;
    }

    try {
        const reponse = await fetch(`${CONFIG.API_URL}/api/rendez-vous`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(donnees)
        });

        const resultat = await reponse.json();

        if (resultat.succes) {
            afficherConfirmation(resultat);
            document.getElementById('formReservation').reset();
            document.getElementById('medecin').disabled = true;
            document.getElementById('heure').disabled = true;
        } else {
            afficherToast(resultat.erreur || 'Erreur lors de la réservation', 'error');
        }

    } catch (erreur) {
        console.error('Erreur:', erreur);

        // Mode démo
        const medecin = state.medecins.find(m => m.id === donnees.medecin_id);
        afficherConfirmation({
            succes: true,
            numero_rdv: 'RDV-' + Math.floor(Math.random() * 9000 + 1000),
            details: {
                'Numéro': 'RDV-' + Math.floor(Math.random() * 9000 + 1000),
                'Médecin': medecin ? medecin.nom : 'Dr. Inconnu',
                'Spécialité': medecin ? medecin.specialite : 'Non spécifié',
                'Date': donnees.date,
                'Heure': donnees.heure,
                'Patient': donnees.nom_patient
            }
        });
        document.getElementById('formReservation').reset();
    }
}

function afficherConfirmation(resultat) {
    const modal = document.getElementById('modal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');

    modalTitle.textContent = '✅ Rendez-vous Confirmé !';

    let detailsHtml = '<div class="confirmation-details">';

    if (resultat.details) {
        for (const [cle, valeur] of Object.entries(resultat.details)) {
            detailsHtml += `
                <div class="detail-row">
                    <span class="detail-label">${cle}</span>
                    <span class="detail-value">${valeur}</span>
                </div>
            `;
        }
    }

    detailsHtml += '</div>';
    detailsHtml += '<p style="margin-top: 20px; text-align: center; color: var(--text-light);">Un SMS de confirmation vous sera envoyé.</p>';

    modalBody.innerHTML = detailsHtml;
    modal.classList.add('active');

    afficherToast('Rendez-vous confirmé avec succès !', 'success');
}

function fermerModal() {
    document.getElementById('modal').classList.remove('active');
}

// ==================== Gestion du Chatbot ====================
function toggleChat() {
    const widget = document.getElementById('chatWidget');
    state.chatOuvert = !state.chatOuvert;

    if (state.chatOuvert) {
        widget.classList.add('active');
        document.getElementById('chatInput').focus();
    } else {
        widget.classList.remove('active');
    }
}

function ouvrirChat() {
    state.chatOuvert = true;
    document.getElementById('chatWidget').classList.add('active');
    document.getElementById('chatInput').focus();
}

function fermerChat() {
    state.chatOuvert = false;
    document.getElementById('chatWidget').classList.remove('active');
}

function gererToucheEntree(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        envoyerMessage();
    }
}

async function envoyerMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message || state.enChargement) return;

    // Ajouter le message de l'utilisateur
    ajouterMessageChat('user', message);
    input.value = '';

    // Afficher l'indicateur de typing
    state.enChargement = true;
    afficherTypingIndicator();

    try {
        const reponse = await fetch(`${CONFIG.API_URL}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                historique_conversation: state.historiqueChat
            })
        });

        const data = await reponse.json();

        // Masquer l'indicateur de typing
        masquerTypingIndicator();

        // Ajouter la réponse du bot
        ajouterMessageChat('bot', data.reponse);

        // Mettre à jour l'historique
        state.historiqueChat = data.historique_conversation;

    } catch (erreur) {
        console.error('Erreur chat:', erreur);
        masquerTypingIndicator();

        // Réponse de démonstration
        const reponseDemo = obtenirReponseDemoChat(message);
        ajouterMessageChat('bot', reponseDemo);
    }

    state.enChargement = false;
}

function envoyerSuggestion(texte) {
    document.getElementById('chatInput').value = texte;
    envoyerMessage();
}

function ajouterMessageChat(type, contenu) {
    const container = document.getElementById('chatMessages');

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;

    const avatar = type === 'bot' ? '🤖' : '👤';

    // Convertir le contenu en HTML (supporter les listes, etc.)
    const contenuHtml = formaterContenuChat(contenu);

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">${contenuHtml}</div>
    `;

    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

function formaterContenuChat(texte) {
    // Convertir les sauts de ligne en <p>
    const paragraphes = texte.split('\n\n');

    return paragraphes.map(p => {
        // Convertir les listes
        if (p.includes('•') || p.includes('-')) {
            const lignes = p.split('\n');
            let html = '<ul>';
            lignes.forEach(ligne => {
                const contenu = ligne.replace(/^[•\-]\s*/, '').trim();
                if (contenu) {
                    html += `<li>${contenu}</li>`;
                }
            });
            html += '</ul>';
            return html;
        }

        // Convertir le gras **texte**
        p = p.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        return `<p>${p}</p>`;
    }).join('');
}

function afficherTypingIndicator() {
    const container = document.getElementById('chatMessages');

    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot';
    typingDiv.id = 'typingIndicator';

    typingDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;

    container.appendChild(typingDiv);
    container.scrollTop = container.scrollHeight;
}

function masquerTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

function obtenirReponseDemoChat(message) {
    const messageLower = message.toLowerCase();

    if (messageLower.includes('bonjour') || messageLower.includes('salut')) {
        return `Bonjour ! 👋 Je suis l'assistant médical de la Clinique Santé+.

Je peux vous aider à :
• 📋 Voir la liste de nos médecins
• 📅 Prendre un rendez-vous
• ⏰ Vérifier les disponibilités
• ❌ Annuler un rendez-vous

Comment puis-je vous aider aujourd'hui ?`;
    }

    if (messageLower.includes('médecin') || messageLower.includes('docteur') || messageLower.includes('liste')) {
        return `👨‍⚕️ **Voici nos médecins disponibles :**

• **Dr. Martin Dupont** - Médecine Générale
  _15 ans d'expérience_

• **Dr. Sophie Bernard** - Cardiologie
  _Spécialiste cardiovasculaire_

• **Dr. Pierre Lambert** - Dentiste
  _Orthodontie et soins dentaires_

• **Dr. Marie Leroy** - Pédiatrie
  _Santé des enfants_

Souhaitez-vous prendre rendez-vous avec l'un d'entre eux ?`;
    }

    if (messageLower.includes('rendez-vous') || messageLower.includes('rdv') || messageLower.includes('réserver')) {
        return `Pour prendre un rendez-vous, j'ai besoin de quelques informations :

1️⃣ **Spécialité** souhaitée
2️⃣ **Date** préférée
3️⃣ **Heure** préférée
4️⃣ Votre **nom** et **téléphone**

Vous pouvez aussi utiliser le formulaire de réservation en bas de page !

Quelle spécialité souhaitez-vous consulter ?`;
    }

    if (messageLower.includes('horaire') || messageLower.includes('ouvert')) {
        return `⏰ **Horaires d'ouverture :**

Notre clinique est ouverte :
• **Lundi - Vendredi** : 9h00 - 17h00
• **Samedi - Dimanche** : Fermé

📍 **Adresse :** 123 Avenue de la Santé, Paris
📞 **Téléphone :** 01 23 45 67 89

Pour les urgences, appelez le **15** (SAMU).`;
    }

    if (messageLower.includes('annuler') || messageLower.includes('supprimer')) {
        return `Pour annuler un rendez-vous, j'ai besoin de :

• Votre **numéro de téléphone**
• Ou votre **numéro de rendez-vous** (ex: RDV-0001)

Pouvez-vous me fournir l'une de ces informations ?`;
    }

    if (messageLower.includes('merci') || messageLower.includes('au revoir')) {
        return `Je vous en prie ! 😊

N'hésitez pas à revenir si vous avez d'autres questions.

Bonne journée et prenez soin de vous ! 🌟`;
    }

    return `Je suis là pour vous aider avec vos rendez-vous médicaux. 🏥

Voici ce que je peux faire :
• **"médecins"** - Voir la liste des médecins
• **"rendez-vous"** - Prendre un rendez-vous
• **"horaires"** - Voir les horaires d'ouverture
• **"annuler"** - Annuler un rendez-vous

Comment puis-je vous aider ?`;
}

// ==================== Authentification ====================
function initialiserAuth() {
    verifierSession();
}

async function verifierSession() {
    try {
        const res = await fetch(`${CONFIG.API_URL}/api/auth/me`, {
            method: 'GET',
            credentials: 'include'
        });
        if (!res.ok) throw new Error();
        state.utilisateur = await res.json();
        majUIAuth();
    } catch {
        state.utilisateur = null;
        majUIAuth();
    }
}

function majUIAuth() {
    const btnAuth = document.getElementById('btnAuth');
    const roleBadge = document.getElementById('roleBadge');
    if (!btnAuth || !roleBadge) return;

    if (state.utilisateur) {
        // User is logged in - show dashboard link
        btnAuth.innerHTML = '👤 Mon Dashboard';
        btnAuth.href = getDashboardUrl(state.utilisateur.role);
        roleBadge.textContent = getRoleIcon(state.utilisateur.role) + ' ' + formatRole(state.utilisateur.role);
        roleBadge.style.display = 'inline-block';
    } else {
        // User is not logged in - show login link
        btnAuth.innerHTML = '🔐 Connexion';
        btnAuth.href = '/login.html';
        roleBadge.style.display = 'none';
    }
}

function getDashboardUrl(role) {
    switch(role) {
        case 'admin':
            return '/dashboard-admin.html';
        case 'secretaire':
            return '/dashboard-secretaire.html';
        case 'medecin':
            return '/dashboard-medecin.html';
        case 'patient':
            return '/dashboard-patient.html';
        default:
            return '/login.html';
    }
}

function formatRole(role) {
    const labels = {
        'admin': 'Admin',
        'secretaire': 'Secrétaire',
        'medecin': 'Médecin',
        'patient': 'Patient'
    };
    return labels[role] || role;
}

function getRoleIcon(role) {
    const icons = {
        'admin': '👑',
        'secretaire': '💼',
        'medecin': '👨‍⚕️',
        'patient': '👤'
    };
    return icons[role] || '👤';
}

// These functions are no longer needed but kept for compatibility
async function toggleAuth() {
    if (state.utilisateur) {
        await deconnexion();
    } else {
        window.location.href = '/login.html';
    }
}

async function ouvrirLogin() {
    window.location.href = '/login.html';
}

async function deconnexion() {
    try {
        await fetch(`${CONFIG.API_URL}/api/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
    } finally {
        state.utilisateur = null;
        majUIAuth();
        afficherToast('Déconnecté', 'info');
    }
}

// ==================== Utilitaires ====================
function afficherToast(message, type = 'info') {
    const toast = document.getElementById('toast');

    const icones = {
        'success': '✅',
        'error': '❌',
        'info': 'ℹ️'
    };

    toast.innerHTML = `${icones[type] || 'ℹ️'} ${message}`;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, CONFIG.DELAI_TOAST);
}

function toggleMenu() {
    const nav = document.querySelector('.nav');
    nav.classList.toggle('active');
}
