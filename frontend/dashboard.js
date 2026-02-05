const API_URL = 'http://localhost:8000';
let currentUser = null;
let allAppointments = [];
let allUsers = [];
let allDoctors = [];

document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
    setupNavigation();
    await loadData();
    setupForms();
});

// ==================== Authentication ====================
async function checkAuth() {
    try {
        const res = await fetch(`${API_URL}/api/auth/me`, { credentials: 'include' });
        if (!res.ok) { window.location.href = '/login.html'; return; }
        currentUser = await res.json();
        updateUserDisplay();
    } catch (e) { window.location.href = '/login.html'; }
}

function updateUserDisplay() {
    const el = (id) => document.getElementById(id);
    if (el('userName')) el('userName').textContent = currentUser.nom;
    if (el('welcomeName')) el('welcomeName').textContent = currentUser.nom.split(' ')[0];
    if (el('profileName')) el('profileName').textContent = currentUser.nom;
    if (el('profileEmail')) el('profileEmail').textContent = currentUser.email;
    if (el('profilePhone')) el('profilePhone').textContent = currentUser.telephone || '-';
}

async function logout() {
    try { await fetch(`${API_URL}/api/auth/logout`, { method: 'POST', credentials: 'include' }); }
    finally { window.location.href = '/login.html'; }
}

// ==================== Navigation ====================
function setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            showSection(item.dataset.section);
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        });
    });
}

function showSection(sectionId) {
    document.querySelectorAll('.dashboard-section').forEach(s => s.classList.remove('active'));
    const section = document.getElementById(`section-${sectionId}`);
    if (section) section.classList.add('active');
}

function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }

// ==================== Data Loading ====================
async function loadData() {
    try {
        if (currentUser.role === 'admin') await loadAdminData();
        else if (currentUser.role === 'secretaire') await loadSecretaryData();
        else if (currentUser.role === 'medecin') await loadDoctorData();
        else if (currentUser.role === 'patient') await loadPatientData();
        await loadDoctorsList();
    } catch (e) { console.error('Error:', e); showToast('Erreur de chargement', 'error'); }
}

async function loadAdminData() {
    const usersRes = await fetch(`${API_URL}/api/admin/users`, { credentials: 'include' });
    if (usersRes.ok) {
        allUsers = await usersRes.json();
        updateEl('totalUsers', allUsers.length);
        updateEl('totalMedecins', allUsers.filter(u => u.role === 'medecin').length);
        renderUsersTable();
    }
    await loadAllAppointments();
}

async function loadSecretaryData() {
    await loadAllAppointments();
    const today = new Date().toISOString().split('T')[0];
    const todayRdv = allAppointments.filter(r => r.date_heure.startsWith(today));
    updateEl('todayRdv', todayRdv.length);
    updateEl('pendingRdv', allAppointments.filter(r => r.statut === 'en_attente').length);
    updateEl('confirmedRdv', allAppointments.filter(r => r.statut === 'confirme').length);
    updateEl('totalRdv', allAppointments.length);
    renderTodayAppointments(todayRdv);
}

async function loadDoctorData() {
    const res = await fetch(`${API_URL}/api/medecin/rendez-vous`, { credentials: 'include' });
    if (res.ok) {
        allAppointments = await res.json();
        const today = new Date().toISOString().split('T')[0];
        const todayRdv = allAppointments.filter(r => r.date_heure.startsWith(today));
        updateEl('todayRdv', todayRdv.length);
        updateEl('weekRdv', allAppointments.length);
        const patients = new Set(allAppointments.map(r => r.patient_id));
        updateEl('totalPatients', patients.size);
        if (todayRdv.length > 0) {
            updateEl('nextRdv', new Date(todayRdv[0].date_heure).toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'}));
        }
        renderDoctorAppointments(todayRdv);
    }
}

async function loadPatientData() {
    updateEl('upcomingRdv', 0);
    updateEl('completedRdv', 0);
    updateEl('nextRdvDate', '-');
    renderPatientAppointments([]);
}

async function loadAllAppointments() {
    const res = await fetch(`${API_URL}/api/admin/rendez-vous`, { credentials: 'include' });
    if (res.ok) {
        allAppointments = await res.json();
        updateEl('totalRdv', allAppointments.length);
        updateEl('rdvConfirmes', allAppointments.filter(r => r.statut === 'confirme').length);
        renderAppointmentsTable();
        renderAllAppointmentsTable();
    }
}

async function loadDoctorsList() {
    const res = await fetch(`${API_URL}/api/medecins`);
    if (res.ok) { allDoctors = await res.json(); renderDoctorsGrid(); }
}

// ==================== Rendering ====================
function renderAppointmentsTable() {
    const tbody = document.getElementById('rdvTableBody');
    if (!tbody) return;
    const recent = allAppointments.slice(0, 10);
    if (recent.length === 0) { tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">Aucun RDV</td></tr>'; return; }
    tbody.innerHTML = recent.map(rdv => {
        const d = new Date(rdv.date_heure);
        return `<tr>
            <td><strong>#${rdv.id}</strong></td>
            <td>${rdv.patient_nom}</td>
            <td>${rdv.medecin_nom}</td>
            <td>${d.toLocaleDateString('fr-FR')}</td>
            <td>${d.toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'})}</td>
            <td><span class="badge ${rdv.statut}">${formatStatus(rdv.statut)}</span></td>
            <td>
                <button class="action-btn edit" onclick="editAppointment(${rdv.id})">✏️</button>
                <button class="action-btn delete" onclick="cancelAppointment(${rdv.id})">❌</button>
            </td>
        </tr>`;
    }).join('');
}

function renderAllAppointmentsTable() {
    const tbody = document.getElementById('allRdvTableBody');
    if (!tbody) return;
    if (allAppointments.length === 0) { tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">Aucun RDV</td></tr>'; return; }
    tbody.innerHTML = allAppointments.map(rdv => {
        const d = new Date(rdv.date_heure);
        return `<tr>
            <td>#${rdv.id}</td>
            <td>${rdv.patient_nom}</td>
            <td>${rdv.patient_telephone || '-'}</td>
            <td>${rdv.medecin_nom}</td>
            <td>${d.toLocaleDateString('fr-FR')}</td>
            <td><span class="badge ${rdv.statut}">${formatStatus(rdv.statut)}</span></td>
            <td>
                <button class="action-btn confirm" onclick="confirmAppointment(${rdv.id})">✅</button>
                <button class="action-btn edit" onclick="editAppointment(${rdv.id})">✏️</button>
                <button class="action-btn delete" onclick="cancelAppointment(${rdv.id})">❌</button>
            </td>
        </tr>`;
    }).join('');
}

function renderTodayAppointments(appointments) {
    const tbody = document.getElementById('todayRdvTableBody');
    if (!tbody) return;
    if (appointments.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="loading-cell">Aucun RDV aujourd\'hui</td></tr>'; return; }
    tbody.innerHTML = appointments.map(rdv => {
        const d = new Date(rdv.date_heure);
        return `<tr>
            <td><strong>${d.toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'})}</strong></td>
            <td>${rdv.patient_nom}</td>
            <td>${rdv.patient_telephone || '-'}</td>
            <td>${rdv.medecin_nom}</td>
            <td><span class="badge ${rdv.statut}">${formatStatus(rdv.statut)}</span></td>
            <td>
                <button class="action-btn confirm" onclick="confirmAppointment(${rdv.id})">✅</button>
                <button class="action-btn edit" onclick="editAppointment(${rdv.id})">✏️</button>
            </td>
        </tr>`;
    }).join('');
}

function renderDoctorAppointments(appointments) {
    const tbody = document.getElementById('todayRdvTableBody');
    if (!tbody) return;
    if (appointments.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="loading-cell">Aucune consultation</td></tr>'; return; }
    tbody.innerHTML = appointments.map(rdv => {
        const d = new Date(rdv.date_heure);
        return `<tr>
            <td><strong>${d.toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'})}</strong></td>
            <td>${rdv.patient_nom}</td>
            <td>${rdv.patient_telephone || '-'}</td>
            <td>${rdv.motif || '-'}</td>
            <td><span class="badge ${rdv.statut}">${formatStatus(rdv.statut)}</span></td>
            <td><button class="action-btn edit" onclick="editAppointment(${rdv.id})">📝</button></td>
        </tr>`;
    }).join('');
}

function renderPatientAppointments(appointments) {
    const container = document.getElementById('appointmentsList');
    if (!container) return;
    if (appointments.length === 0) {
        container.innerHTML = `<div style="text-align:center;padding:40px;">
            <p style="font-size:48px;">📅</p>
            <h3>Aucun rendez-vous</h3>
            <p style="color:#666;">Prenez votre premier rendez-vous</p>
            <button class="btn btn-primary" onclick="showSection('new-appointment')">➕ Nouveau RDV</button>
        </div>`;
        return;
    }
    container.innerHTML = appointments.map(rdv => {
        const d = new Date(rdv.date_heure);
        return `<div class="appointment-item">
            <div class="appointment-date">
                <span class="day">${d.getDate()}</span>
                <span class="month">${d.toLocaleDateString('fr-FR', {month:'short'})}</span>
            </div>
            <div class="appointment-info">
                <h4>${rdv.medecin_nom}</h4>
                <p>🕐 ${d.toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'})}</p>
            </div>
            <span class="badge ${rdv.statut}">${formatStatus(rdv.statut)}</span>
        </div>`;
    }).join('');
}

function renderUsersTable() {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;
    if (allUsers.length === 0) { tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">Aucun utilisateur</td></tr>'; return; }
    tbody.innerHTML = allUsers.map(u => `<tr>
        <td>#${u.id}</td>
        <td>${u.nom}</td>
        <td>${u.email || '-'}</td>
        <td><span class="badge ${u.role}">${formatRole(u.role)}</span></td>
        <td><span class="badge ${u.est_actif ? 'confirme' : 'annule'}">${u.est_actif ? 'Actif' : 'Inactif'}</span></td>
    </tr>`).join('');
}

function renderDoctorsGrid() {
    const container = document.getElementById('doctorsGrid');
    if (!container) return;
    if (allDoctors.length === 0) { container.innerHTML = '<p style="padding:20px;">Aucun médecin</p>'; return; }
    const icons = {'Médecine Générale':'👨‍⚕️','Cardiologie':'❤️','Dentiste':'🦷','Pédiatrie':'👶'};
    container.innerHTML = allDoctors.map(d => `<div class="doctor-card">
        <div class="doctor-avatar">${icons[d.specialite] || '👨‍⚕️'}</div>
        <h4>${d.nom}</h4>
        <p class="speciality">${d.specialite}</p>
    </div>`).join('');
}

// ==================== Forms ====================
function setupForms() {
    const form = document.getElementById('newRdvForm');
    if (form) form.addEventListener('submit', handleNewAppointment);
    const dateInput = document.getElementById('rdvDate');
    if (dateInput) dateInput.min = new Date().toISOString().split('T')[0];
}

async function loadDoctorsBySpeciality() {
    const spec = document.getElementById('speciality').value;
    const docSelect = document.getElementById('doctor');
    docSelect.innerHTML = '<option value="">Choisir...</option>';
    docSelect.disabled = true;
    if (!spec) return;
    const filtered = allDoctors.filter(d => d.specialite === spec);
    filtered.forEach(d => { const o = document.createElement('option'); o.value = d.id; o.textContent = d.nom; docSelect.appendChild(o); });
    docSelect.disabled = false;
}

async function loadTimeSlots() {
    const docId = document.getElementById('doctor').value;
    const date = document.getElementById('rdvDate').value;
    const timeSelect = document.getElementById('rdvTime');
    timeSelect.innerHTML = '<option value="">Choisir...</option>';
    timeSelect.disabled = true;
    if (!docId || !date) return;
    try {
        const res = await fetch(`${API_URL}/api/medecins/${docId}/disponibilites?date=${date}`);
        const data = await res.json();
        if (data.creneaux_disponibles?.length > 0) {
            data.creneaux_disponibles.forEach(s => { const o = document.createElement('option'); o.value = s; o.textContent = s; timeSelect.appendChild(o); });
            timeSelect.disabled = false;
        } else { timeSelect.innerHTML = '<option value="">Aucun créneau</option>'; }
    } catch (e) { console.error(e); }
}

async function handleNewAppointment(e) {
    e.preventDefault();
    const data = {
        medecin_id: parseInt(document.getElementById('doctor').value),
        nom_patient: document.getElementById('patientName')?.value || currentUser.nom,
        telephone_patient: document.getElementById('patientPhone')?.value || currentUser.telephone || '0600000000',
        date: document.getElementById('rdvDate').value,
        heure: document.getElementById('rdvTime').value,
        motif: document.getElementById('rdvMotif')?.value || ''
    };
    try {
        const res = await fetch(`${API_URL}/api/rendez-vous`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (result.succes) {
            showToast('RDV créé!', 'success');
            e.target.reset();
            document.getElementById('doctor').disabled = true;
            document.getElementById('rdvTime').disabled = true;
            await loadData();
            showSection('overview');
        } else { showToast(result.erreur || 'Erreur', 'error'); }
    } catch (err) { showToast('Erreur', 'error'); }
}

// ==================== Actions ====================
async function confirmAppointment(id) {
    try {
        const res = await fetch(`${API_URL}/api/admin/rendez-vous/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ statut: 'confirme' })
        });
        if (res.ok) { showToast('Confirmé', 'success'); await loadData(); }
    } catch (e) { showToast('Erreur', 'error'); }
}

async function cancelAppointment(id) {
    if (!confirm('Annuler ce RDV?')) return;
    try {
        const res = await fetch(`${API_URL}/api/rendez-vous/${id}`, { method: 'DELETE', credentials: 'include' });
        if (res.ok) { showToast('Annulé', 'success'); await loadData(); }
    } catch (e) { showToast('Erreur', 'error'); }
}

function editAppointment(id) {
    const rdv = allAppointments.find(r => r.id === id);
    if (!rdv) return;
    const modal = document.getElementById('editModal');
    const modalBody = document.getElementById('modalBody');
    const saveBtn = document.getElementById('modalSaveBtn');
    modalBody.innerHTML = `
        <div class="form-group">
            <label>Statut</label>
            <select id="editStatus">
                <option value="en_attente" ${rdv.statut === 'en_attente' ? 'selected' : ''}>En attente</option>
                <option value="confirme" ${rdv.statut === 'confirme' ? 'selected' : ''}>Confirmé</option>
                <option value="termine" ${rdv.statut === 'termine' ? 'selected' : ''}>Terminé</option>
                <option value="annule" ${rdv.statut === 'annule' ? 'selected' : ''}>Annulé</option>
            </select>
        </div>
        <div class="form-group">
            <label>Notes</label>
            <textarea id="editNotes" rows="3">${rdv.notes || ''}</textarea>
        </div>`;
    saveBtn.onclick = async () => {
        try {
            const res = await fetch(`${API_URL}/api/admin/rendez-vous/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    statut: document.getElementById('editStatus').value,
                    notes: document.getElementById('editNotes').value
                })
            });
            if (res.ok) { showToast('Mis à jour', 'success'); closeModal(); await loadData(); }
        } catch (e) { showToast('Erreur', 'error'); }
    };
    modal.classList.add('active');
}

function closeModal() { document.getElementById('editModal')?.classList.remove('active'); }

async function refreshData() { showToast('Actualisation...', 'info'); await loadData(); showToast('Actualisé', 'success'); }

function filterAppointments() {
    const status = document.getElementById('filterStatus')?.value;
    const tbody = document.getElementById('allRdvTableBody');
    if (!tbody) return;
    let filtered = status ? allAppointments.filter(r => r.statut === status) : allAppointments;
    if (filtered.length === 0) { tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">Aucun résultat</td></tr>'; return; }
    tbody.innerHTML = filtered.map(rdv => {
        const d = new Date(rdv.date_heure);
        return `<tr>
            <td>#${rdv.id}</td>
            <td>${rdv.patient_nom}</td>
            <td>${rdv.patient_telephone || '-'}</td>
            <td>${rdv.medecin_nom}</td>
            <td>${d.toLocaleDateString('fr-FR')}</td>
            <td><span class="badge ${rdv.statut}">${formatStatus(rdv.statut)}</span></td>
            <td>
                <button class="action-btn confirm" onclick="confirmAppointment(${rdv.id})">✅</button>
                <button class="action-btn edit" onclick="editAppointment(${rdv.id})">✏️</button>
                <button class="action-btn delete" onclick="cancelAppointment(${rdv.id})">❌</button>
            </td>
        </tr>`;
    }).join('');
}

function filterByDate() { /* Implement if needed */ }
function loadSchedule() { /* Implement if needed */ }

// ==================== Utilities ====================
function updateEl(id, value) { const el = document.getElementById(id); if (el) el.textContent = value; }
function formatStatus(s) { return {'confirme':'Confirmé','en_attente':'En attente','annule':'Annulé','termine':'Terminé'}[s] || s; }
function formatRole(r) { return {'admin':'👑 Admin','secretaire':'💼 Secrétaire','medecin':'👨‍⚕️ Médecin','patient':'👤 Patient'}[r] || r; }

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => toast.classList.remove('show'), 3000);
}

