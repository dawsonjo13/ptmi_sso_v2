# FastAPI SSO with JWT and SQL Server

A complete REST API for a custom centralized login/SSO service using FastAPI, JWT, SQL Server, and SMTP email reset links.

## Features

- Login with `KPK` and password
- First login uses employee `dob` value as the default password
- Passwords are stored in `auth_user` using bcrypt hashing
- Access token + refresh token flow
- Refresh token is stored hashed in `auth_session`
- Logout invalidates only the current device/session
- Forgot password using email reset token link
- Reset password with secure token
- Change password for authenticated users
- Read-only `employee` table
- Failed login tracking, lockout, active status outside employee table

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create SQL Server tables

Run:

```sql
sql/001_create_auth_schema.sql
```

The script does not modify the existing `employee` table.

### 3. Configure environment

Copy `.env.example` to `.env` and update the values.

```bash
copy .env.example .env
```

### 4. Run API

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000/docs
```

## Main endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Login using KPK and password |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Logout current device/session |
| POST | `/auth/forgot-password` | Send password reset email |
| POST | `/auth/reset-password` | Reset password using email token |
| POST | `/auth/change-password` | Change password while logged in |
| GET | `/auth/me` | Get current authenticated user |

## Employee table assumption

The app assumes this existing table:

```sql
employee(
    KPK varchar(6) primary key,
    name varchar(100),
    dob varchar(8),
    email varchar(255),
    supervisor varchar(6),
    join_date varchar(50)
)
```

`dob` must be stored as `YYYYMMDD`, for example `19981231`.

## Password policy

Passwords must contain:

- At least 8 characters
- At least one uppercase letter
- At least one lowercase letter

## Notes

For production, use HTTPS only, a strong JWT secret, restricted CORS origins, secure SMTP credentials, and regular cleanup of expired sessions/reset tokens.
