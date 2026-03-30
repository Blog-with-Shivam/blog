# Deployment guide

## Environment variables

Set these in your host or secret manager:

- `SECRET_KEY` — long random string
- `ADMIN_USERNAME` — admin login name
- `ADMIN_PASSWORD` — strong initial password
- `DATABASE_URL` — PostgreSQL URL in production
- `FORCE_HTTPS=true`
- `SESSION_COOKIE_SECURE=true`
- `MAX_CONTENT_LENGTH_MB=50`
- `SESSION_MINUTES=30`

## Local development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Production build

Use Gunicorn:

```bash
gunicorn -w 2 -b 0.0.0.0:8000 app:app
```

## Render

1. Create a new Web Service.
2. Connect the repository.
3. Set the build command to `pip install -r requirements.txt`.
4. Set the start command to `gunicorn app:app`.
5. Add the environment variables above.
6. Set the database to PostgreSQL and copy the URL into `DATABASE_URL`.

## Railway

1. Create a new service from the repository.
2. Add a PostgreSQL database.
3. Copy the database URL into `DATABASE_URL`.
4. Set the same environment variables.
5. Use `gunicorn app:app` as the start command.

## Frontend hosting option

The frontend is already served by Flask, so Vercel is optional. If you separate the frontend later, you will need to keep API calls pointed at the Flask backend and handle CORS properly. For this project, a single backend deployment is the cleaner choice.

## Security checklist

- Use HTTPS only.
- Keep `SESSION_COOKIE_SECURE=true`.
- Keep `FORCE_HTTPS=true` in production.
- Rotate `SECRET_KEY` only when you are ready to invalidate sessions.
- Use PostgreSQL instead of SQLite for real production traffic.
- Back up the database and uploaded files.
