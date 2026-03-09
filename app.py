from flask import Flask, render_template, request, redirect, url_for, abort, make_response
import sqlite3
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)

DB_PATH    = "feedback.db"
ADMIN_ROLE = "adminxklyjj"
USER_ROLE  = "user"
PER_PAGE   = 8

# ─────────────────────────── COOKIE HELPERS ────────────────────────

def get_role():
    """Read the role cookie. Returns 'user' if missing or unrecognized."""
    role = request.cookies.get("role", USER_ROLE)
    # only accept known roles — anything else is treated as user
    return role if role == ADMIN_ROLE else USER_ROLE

def is_admin():
    return get_role() == ADMIN_ROLE

def set_role_cookie(response, role):
    """Attach the role cookie to a response."""
    response.set_cookie(
        "role",
        role,
        max_age=60 * 60 * 24 * 30,   # 30 days
        httponly=False,               # must be False so browser devtools can edit it
        samesite="Lax"
    )
    return response

# ─────────────────────────── DB HELPERS ────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                subject    TEXT    NOT NULL DEFAULT 'No subject',
                rating     INTEGER NOT NULL,
                message    TEXT    NOT NULL,
                category   TEXT    NOT NULL DEFAULT 'general',
                created_at TEXT    NOT NULL
            )
        """)

# ─────────────────────────── ROUTES ────────────────────────────────

@app.route("/")
def index():
    resp = make_response(render_template("index.html", is_admin=is_admin()))
    # Give every new visitor a 'user' role cookie if they don't have one yet
    if "role" not in request.cookies:
        set_role_cookie(resp, USER_ROLE)
    return resp


@app.route("/submit", methods=["POST"])
def submit():
    subject  = request.form.get("subject",  "").strip()
    rating   = request.form.get("rating",   "").strip()
    message  = request.form.get("message",  "").strip()
    category = request.form.get("category", "general").strip()

    if not message or not rating:
        return redirect(url_for("index", error=1))

    with get_db() as conn:
        conn.execute(
            "INSERT INTO feedback (subject, rating, message, category, created_at) VALUES (?,?,?,?,?)",
            (subject or "No subject", int(rating), message, category, datetime.now().isoformat())
        )
    return redirect(url_for("view_feedback"))


# ── LIST ────────────────────────────────────────────────────────────
@app.route("/feedback")
def view_feedback():
    page     = max(1, request.args.get("page", 1, type=int))
    category = request.args.get("category", "all")
    offset   = (page - 1) * PER_PAGE

    with get_db() as conn:
        where  = "WHERE category = ?" if category != "all" else ""
        params = (category,) if category != "all" else ()

        total = conn.execute(
            f"SELECT COUNT(*) FROM feedback {where}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"SELECT * FROM feedback {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            (*params, PER_PAGE, offset)
        ).fetchall()

        stats = conn.execute(
            "SELECT COUNT(*) as count, ROUND(AVG(rating),1) as avg_rating FROM feedback"
        ).fetchone()

    feedback_list = [dict(r) for r in rows]
    for f in feedback_list:
        f["timestamp"] = _fmt(f["created_at"])

    total_pages = max(1, -(-total // PER_PAGE))

    resp = make_response(render_template(
        "feedback.html",
        feedback    = feedback_list,
        avg_rating  = stats["avg_rating"] or 0,
        count       = stats["count"] or 0,
        page        = page,
        total_pages = total_pages,
        category    = category,
        per_page    = PER_PAGE,
        total       = total,
        is_admin    = is_admin(),
    ))
    if "role" not in request.cookies:
        set_role_cookie(resp, USER_ROLE)
    return resp


# ── DETAIL ──────────────────────────────────────────────────────────
@app.route("/feedback/<int:fid>")
def feedback_detail(fid):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM feedback WHERE id = ?", (fid,)).fetchone()
    if row is None:
        abort(404)
    item = dict(row)
    item["timestamp"] = _fmt(item["created_at"])

    resp = make_response(render_template("detail.html", item=item, is_admin=is_admin()))
    if "role" not in request.cookies:
        set_role_cookie(resp, USER_ROLE)
    return resp


# ── ANALYTICS ───────────────────────────────────────────────────────
@app.route("/analytics")
def analytics():
    with get_db() as conn:
        all_rows = conn.execute(
            "SELECT rating, category, created_at FROM feedback"
        ).fetchall()

    if not all_rows:
        return render_template("analytics.html", empty=True, is_admin=is_admin())

    rating_dist = defaultdict(int)
    for r in all_rows:
        rating_dist[r["rating"]] += 1

    cat_counts = defaultdict(int)
    for r in all_rows:
        cat_counts[r["category"]] += 1

    daily = defaultdict(int)
    for r in all_rows:
        day = r["created_at"][:10]
        daily[day] += 1

    sorted_days = sorted(daily.items())[-14:]
    avg = round(sum(r["rating"] for r in all_rows) / len(all_rows), 2)

    return render_template(
        "analytics.html",
        empty        = False,
        total        = len(all_rows),
        avg          = avg,
        rating_dist  = dict(rating_dist),
        cat_counts   = dict(cat_counts),
        trend_days   = [d[0] for d in sorted_days],
        trend_counts = [d[1] for d in sorted_days],
        is_admin     = is_admin(),
    )


# ── DELETE (admin cookie required) ──────────────────────────────────
@app.route("/delete/<int:fid>", methods=["POST"])
def delete_feedback(fid):
    """
    Only works if the request has role=adminxklyjj cookie.
    Users can't do this unless they manually edit their cookie in devtools.
    """
    if not is_admin():
        abort(403)   # Forbidden — role cookie is not admin
    with get_db() as conn:
        conn.execute("DELETE FROM feedback WHERE id = ?", (fid,))
    return redirect(url_for("view_feedback"))


# ─────────────────────────── HELPERS ───────────────────────────────

def _fmt(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%B %d, %Y at %I:%M %p")
    except Exception:
        return iso


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
