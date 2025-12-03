# SupportHub

A minimal Django REST setup to kick off authentication for the support ticket system.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Apply migrations:
   ```bash
   python manage.py migrate
   ```
3. Create a superuser (optional, for admin access):
   ```bash
   python manage.py createsuperuser
   ```
4. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Auth API
- `POST /api/auth/login/` – returns a token and user profile for valid credentials.
- `POST /api/auth/logout/` – revokes the current token.
- `GET /api/auth/whoami/` – returns the authenticated user's profile.

See `supporthub/accounts/tests.py` for example flows.
