"""GEO Platform - 用户认证与多租户"""
import bcrypt
import jwt
import time
import os
import re
from typing import Optional, List
from models import get_db

JWT_SECRET = os.environ.get("GEO_JWT_SECRET", "geo-platform-secret-2026")
JWT_EXPIRE = 7 * 24 * 3600  # 7天
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

PLAN_FREE = "free"
PLAN_PRO = "pro"
PLAN_ENTERPRISE = "enterprise"

PLAN_LIMITS = {
    PLAN_FREE: {"companies": 1, "monitors_per_month": 10, "reports_per_month": 3},
    PLAN_PRO: {"companies": 10, "monitors_per_month": 100, "reports_per_month": 50},
    PLAN_ENTERPRISE: {"companies": 999, "monitors_per_month": 9999, "reports_per_month": 9999},
}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_token(user_id: int, email: str, plan: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "plan": plan,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRE,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def register(email: str, password: str, name: str, company_name: str = "") -> dict:
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        return {"error": "邮箱格式不正确"}
    if len(password) < 6:
        return {"error": "密码至少6位"}
    if not name.strip():
        return {"error": "姓名不能为空"}

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        conn.close()
        return {"error": "该邮箱已注册"}

    pw_hash = hash_password(password)
    cursor = conn.execute(
        "INSERT INTO users (email, password_hash, name, plan) VALUES (?, ?, ?, ?)",
        (email, pw_hash, name.strip(), PLAN_FREE),
    )
    user_id = cursor.lastrowid

    if company_name.strip():
        conn.execute(
            "INSERT INTO companies (name, domain, owner_id) VALUES (?, ?, ?)",
            (company_name.strip(), "", user_id),
        )

    conn.commit()
    conn.close()

    token = create_token(user_id, email, PLAN_FREE)
    return {
        "token": token,
        "user": {"id": user_id, "email": email, "name": name.strip(), "plan": PLAN_FREE},
    }


def login(email: str, password: str) -> dict:
    email = email.strip().lower()
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    if not row:
        return {"error": "邮箱未注册"}
    if not verify_password(password, row["password_hash"]):
        return {"error": "密码错误"}

    token = create_token(row["id"], row["email"], row["plan"])
    return {
        "token": token,
        "user": {"id": row["id"], "email": row["email"], "name": row["name"], "plan": row["plan"]},
    }


def get_user(user_id: int) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT id, email, name, plan, created_at FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_companies(user_id: int) -> List[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM companies WHERE owner_id=? ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def check_plan_limit(user_id: int, limit_type: str) -> bool:
    user = get_user(user_id)
    if not user:
        return False
    plan = user.get("plan", PLAN_FREE)
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS[PLAN_FREE])
    max_val = limits.get(limit_type, 0)

    conn = get_db()
    if limit_type == "companies":
        count = conn.execute("SELECT COUNT(*) FROM companies WHERE owner_id=?", (user_id,)).fetchone()[0]
    elif limit_type == "monitors_per_month":
        count = conn.execute(
            "SELECT COUNT(*) FROM monitor_snapshots ms JOIN companies c ON ms.company_id=c.id "
            "WHERE c.owner_id=? AND ms.created_at >= date('now','-30 days')",
            (user_id,),
        ).fetchone()[0]
    elif limit_type == "reports_per_month":
        count = conn.execute(
            "SELECT COUNT(*) FROM geo_reports r JOIN companies c ON r.company_id=c.id "
            "WHERE c.owner_id=? AND r.created_at >= date('now','-30 days')",
            (user_id,),
        ).fetchone()[0]
    else:
        count = 0
    conn.close()
    return count < max_val
