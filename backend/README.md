# Backend Admin API

## Overview
Adds session-cookie auth, role-based access, admin/medecin rendez-vous management, and notification placeholders.

## Seeded users
- Admin: `admin@clinique.fr` / `admin123`
- Secrétaire: `secretariat@clinique.fr` / `admin123`
- Médecins: `martin.dupont@clinique.fr` etc. / `medecin123`
- Patient: `patient@test.fr` / `patient123`

## Run
```powershell
cd C:\Users\maxst\Downloads\medical-appointment-system\backend
pip install -r requirements.txt
python main.py
```

## Auth usage (session cookies)
1. `POST /api/auth/login` with JSON: `{ "email": "admin@clinique.fr", "mot_de_passe": "admin123" }`
2. The server sets `session_token` HTTP-only cookie.
3. Protected endpoints require the cookie; use the same client session.
4. Logout: `POST /api/auth/logout`.

## Admin endpoints
- `GET /api/admin/users`
- `GET /api/admin/rendez-vous`
- `PATCH /api/admin/rendez-vous/{id}`
- `POST /api/admin/notifications`
- `POST /api/admin/ml/placeholder`

## Medecin endpoints
- `GET /api/medecin/rendez-vous`
