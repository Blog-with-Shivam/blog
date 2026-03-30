# Blog with Shivam

A secure Flask cybersecurity blog with:
- Admin-only publishing
- Password hashing
- Session auth
- CSRF protection
- SQLite for development
- PostgreSQL-ready database layer
- File uploads for images, PDFs, and MP4 videos
- YouTube embeds
- Search, category filter, tags, and pagination

## Folder structure

```
project-root
├── app.py
├── requirements.txt
├── templates/
│   ├── index.html
│   └── admin.html
├── static/
│   ├── style.css
│   └── script.js
├── uploads/
└── blog.db
```

## Install

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## Configure environment variables

Set these before first run:

```bash
export SECRET_KEY="replace-with-a-long-random-string"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="strong-password-here"
export FORCE_HTTPS="false"   # keep false locally
```

Optional production settings:

```bash
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
export SESSION_COOKIE_SECURE="true"
export MAX_CONTENT_LENGTH_MB="50"
export SESSION_MINUTES="30"
```

## Run locally

```bash
python app.py
```

Open:
- Public site: http://127.0.0.1:5000/
- Admin panel: http://127.0.0.1:5000/admin

## Production run

Use Gunicorn:

```bash
gunicorn -w 2 -b 0.0.0.0:8000 app:app
```

## Notes

- The first time the app starts, it creates the admin account from `ADMIN_USERNAME` and `ADMIN_PASSWORD` if no admin exists yet.
- If you change credentials later, update the database manually or reset the database.
- Uploads are limited to `png`, `jpg`, `jpeg`, `pdf`, and `mp4`.
