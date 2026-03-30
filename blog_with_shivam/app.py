import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import bleach
import markdown as md
from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# =====================
# CONFIG
# =====================
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "mp4"}

ALLOWED_MIME_PREFIXES = {
    "image": {"image/png", "image/jpeg"},
    "pdf": {"application/pdf"},
    "video": {"video/mp4", "application/mp4"},
}

MAX_CONTENT_LENGTH_MB = int(os.environ.get("MAX_CONTENT_LENGTH_MB", "50"))
SESSION_MINUTES = int(os.environ.get("SESSION_MINUTES", "30"))

FORCE_HTTPS = os.environ.get("FORCE_HTTPS", "false").lower() in {
    "1", "true", "yes", "on"
}

# =====================
# APP INIT
# =====================
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'blog.db'}",
)

if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config[
        "SQLALCHEMY_DATABASE_URI"
    ].replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH_MB * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=SESSION_MINUTES)

db = SQLAlchemy(app)

# =====================
# SECURITY CONFIG
# =====================
SAFE_TAGS = [
    "p","br","strong","em","ul","ol","li","blockquote",
    "code","pre","hr","h1","h2","h3","h4","h5","h6","a","span",
]

SAFE_ATTRS = {
    "a": ["href", "title", "rel", "target"],
    "span": ["class"],
}

SAFE_PROTOCOLS = ["http", "https", "mailto"]

# =====================
# MODELS
# =====================
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False)
    slug = db.Column(db.String(260), unique=True, nullable=False)
    content_markdown = db.Column(db.Text, nullable=False)
    content_html = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(120), default="General")
    tags = db.Column(db.String(500), default="")

    attachment_path = db.Column(db.String(500))
    attachment_name = db.Column(db.String(255))
    attachment_mime = db.Column(db.String(100))

    youtube_url = db.Column(db.String(500))
    youtube_embed_url = db.Column(db.String(500))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def tag_list(self):
        return [t.strip() for t in (self.tags or "").split(",") if t.strip()]

# =====================
# HELPERS
# =====================
def is_admin_logged_in():
    return bool(session.get("admin_id"))

def current_admin():
    if not session.get("admin_id"):
        return None
    return db.session.get(Admin, session["admin_id"])

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_admin_logged_in():
            return jsonify({"ok": False, "error": "Login required"}), 401
        return view(*args, **kwargs)
    return wrapped

def ensure_csrf_token():
    if not session.get("csrf_token"):
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]

# =====================
# SECURITY MIDDLEWARE
# =====================
@app.before_request
def before_request():
    session.permanent = True
    ensure_csrf_token()

    if request.method in {"POST", "PUT", "DELETE"}:
        token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if token != session.get("csrf_token"):
            return jsonify({"ok": False, "error": "Invalid or missing CSRF token"}), 400

# =====================
# UTIL
# =====================
def slugify(text):
    return re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")

def unique_slug(base):
    slug = base
    i = 2
    while Post.query.filter_by(slug=slug).first():
        slug = f"{base}-{i}"
        i += 1
    return slug

def sanitize_markdown(text):
    html = md.markdown(text or "")
    return bleach.clean(html, tags=SAFE_TAGS, attributes=SAFE_ATTRS)

# =====================
# ROUTES
# =====================
@app.route("/")
def index():
    q = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    tag = (request.args.get("tag") or "").strip()

    page = int(request.args.get("page", 1))
    per_page = 6

    query = Post.query

    # 🔍 Search
    if q:
        query = query.filter(
            db.or_(
                Post.title.ilike(f"%{q}%"),
                Post.content_markdown.ilike(f"%{q}%"),
                Post.category.ilike(f"%{q}%"),
                Post.tags.ilike(f"%{q}%"),
            )
        )

    # 📂 Category filter
    if category:
        query = query.filter(func.lower(Post.category) == category.lower())

    # 🏷 Tag filter
    if tag:
        query = query.filter(Post.tags.ilike(f"%{tag}%"))

    # 📄 Pagination
    pagination = query.order_by(Post.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # 📊 Categories & Tags (for dropdowns)
    categories = [
        row[0]
        for row in db.session.query(Post.category)
        .distinct()
        .order_by(Post.category.asc())
        .all()
        if row[0]
    ]

    tag_rows = db.session.query(Post.tags).all()
    tags = sorted({
        t.strip()
        for row in tag_rows
        for t in (row[0] or "").split(",")
        if t.strip()
    })

    return render_template(
        "index.html",
        posts=pagination.items,
        pagination=pagination,
        categories=categories,
        tags=tags,
        search_query=q,
        active_category=category,
        active_tag=tag,
        csrf_token=ensure_csrf_token(),
    )

@app.route("/admin")
def admin_page():
    return render_template(
        "admin.html",
        csrf_token=ensure_csrf_token(),
        logged_in=is_admin_logged_in(),
        admin_username=(current_admin().username if current_admin() else ""),
    )

@app.route("/api/session")
def session_api():
    admin = current_admin()
    return jsonify({
        "ok": True,
        "logged_in": bool(admin),
        "username": admin.username if admin else None,
        "csrf_token": ensure_csrf_token(),
    })

# =====================
# LOGIN (FIXED)
# =====================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.form
    username = data.get("username")
    password = data.get("password")

    admin = Admin.query.filter_by(username=username).first()

    if not admin or not check_password_hash(admin.password_hash, password):
        return jsonify({"ok": False, "error": "Invalid credentials"}), 401

    session.clear()
    session["admin_id"] = admin.id

    new_token = ensure_csrf_token()

    return jsonify({"ok": True, "csrf_token": new_token})

@app.route("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})

# =====================
# POSTS
# =====================
@app.route("/api/posts", methods=["POST"])
@login_required
def create_post():
    title = request.form.get("title")
    content = request.form.get("content")

    post = Post(
        title=title,
        slug=unique_slug(slugify(title)),
        content_markdown=content,
        content_html=sanitize_markdown(content),
    )

    db.session.add(post)
    db.session.commit()

    return jsonify({"ok": True})

# =====================
# BOOTSTRAP
# =====================
def bootstrap_admin():
    if Admin.query.count() == 0:
        admin = Admin(
            username=os.environ.get("ADMIN_USERNAME", "admin"),
            password_hash=generate_password_hash(
                os.environ.get("ADMIN_PASSWORD", "1234")
            ),
        )
        db.session.add(admin)
        db.session.commit()

with app.app_context():
    db.create_all()
    bootstrap_admin()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)