// Minimal auth helpers used by the login page to call session-based API
const API_URL = 'http://localhost:8000';

async function apiLogin(email, mot_de_passe) {
    const res = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, mot_de_passe })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Identifiants invalides');
    return data;
}

async function apiMe() {
    const res = await fetch(`${API_URL}/api/auth/me`, { credentials: 'include' });
    if (!res.ok) return null;
    return res.json();
}

async function apiLogout() {
    await fetch(`${API_URL}/api/auth/logout`, { method: 'POST', credentials: 'include' });
}

export { apiLogin, apiMe, apiLogout, API_URL };

