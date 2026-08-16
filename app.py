"""GEO Platform - Flask后端"""
from flask import Flask, jsonify, request, send_from_directory, Response, g
from models import init_db, seed_mzy_data, get_db
from auth import register, login, get_user, decode_token, get_user_companies, check_plan_limit, create_token, PLAN_LIMITS
from agents import get_agent
from agents.pdf_report import generate_report_html
from agents.keyword_expander import expand_keywords, get_expanded_keywords
from agents.company_ingest import ingest_company_website, normalize_company_url
from agents.rag_chat import chat, chat_stream, get_channels, get_conversations
from agents.scheduler import (
    _take_snapshot, get_trend_data, get_scheduled_jobs,
    create_scheduled_job, toggle_scheduled_job, delete_scheduled_job,
    init_scheduler, reload_scheduler,
)
from agents.geo_benchmark import run_benchmark, start_benchmark_async, get_benchmark_status
from agents.sheep_scorer import calculate_gem_score, get_model_weights as get_cn_model_weights, build_evidence_from_diagnosis
from agents.content_strategies import apply_strategy, apply_all_strategies, get_strategies_info
from agents.compliance_auditor import check_compliance, get_rules as get_compliance_rules
from agents.gdo_auditor import audit_decision_evidence, get_dimensions as get_gdo_dimensions, simulate_ai_decision_query
from agents.ai_comparison import run_decision_test, get_scenarios as get_decision_scenarios
from agents.maturity_scorer import calculate_maturity, get_layers as get_maturity_layers
from agents.geo_ab_test import create_test_suite, run_test_batch, compare_phases, get_test_suites, get_page_types, get_source_categories
from agents.pdf_dedup import audit_website_pdfs, audit_duplicate_pdfs
from config import PORT, DEBUG
import os
import json

# 异步任务存储（app.py全局，避免模块间状态问题）
_BENCHMARK_TASKS = {}

app = Flask(__name__, static_folder="static", static_url_path="/static")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": "0.1.0", "auth_enabled": bool(GEO_API_TOKEN)})


# API认证中间件
GEO_API_TOKEN = os.environ.get("GEO_API_TOKEN", "")
AUTH_EXEMPT_PATHS = {"/health", "/", "/api/auth/register", "/api/auth/login"}


@app.before_request
def check_auth():
    path = request.path
    if path in AUTH_EXEMPT_PATHS or path.startswith("/static"):
        return None

    # 模式1: 服务间Token（GEO_API_TOKEN）
    if GEO_API_TOKEN:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer ") and auth_header[7:] == GEO_API_TOKEN:
            return None
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    # 模式2: JWT用户认证
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": "请先登录"}), 401

    payload = decode_token(auth_header[7:])
    if not payload:
        return jsonify({"success": False, "error": "登录已过期，请重新登录"}), 401

    g.current_user = payload
    return None


# ========== 用户认证 ==========

@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(silent=True) or {}
    result = register(
        email=data.get("email", ""),
        password=data.get("password", ""),
        name=data.get("name", ""),
        company_name=data.get("company_name", ""),
    )
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or {}
    result = login(
        email=data.get("email", ""),
        password=data.get("password", ""),
    )
    if "error" in result:
        return jsonify(result), 401
    return jsonify(result)


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    user = getattr(g, "current_user", None)
    if not user:
        return jsonify({"error": "未登录"}), 401
    user_info = get_user(user["user_id"])
    if not user_info:
        return jsonify({"error": "用户不存在"}), 404
    return jsonify({"user": user_info})


# ========== 公司 ==========

@app.route("/api/companies", methods=["GET"])
def list_companies():
    user = getattr(g, "current_user", None)
    conn = get_db()
    if user:
        rows = conn.execute("SELECT * FROM companies WHERE owner_id=? ORDER BY id DESC", (user["user_id"],)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM companies ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/companies/<int:cid>", methods=["GET"])
def get_company(cid):
    conn = get_db()
    row = conn.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@app.route("/api/companies", methods=["POST"])
def create_company():
    user = getattr(g, "current_user", None)
    if not user:
        return jsonify({"error": "未登录"}), 401
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    domain = data.get("domain", "").strip()
    if not name:
        return jsonify({"error": "企业名称不能为空"}), 400
    if not check_plan_limit(user["user_id"], "companies"):
        plan = user.get("plan", "free")
        return jsonify({"error": f"当前套餐({plan})已达企业数量上限，请升级套餐"}), 403

    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO companies (name, domain, owner_id, industry, city, description) VALUES (?, ?, ?, ?, ?, ?)",
        (name, domain, user["user_id"],
         data.get("industry", ""), data.get("city", ""), data.get("description", "")),
    )
    cid = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"id": cid, "name": name, "domain": domain})


# ========== 竞争对手追踪 ==========

@app.route("/api/competitors/<int:company_id>", methods=["GET"])
def list_competitors(company_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM competitors WHERE company_id=? ORDER BY geo_score DESC",
        (company_id,),
    ).fetchall()
    conn.close()
    return jsonify({"success": True, "data": [dict(r) for r in rows]})


@app.route("/api/competitors/<int:company_id>", methods=["POST"])
def add_competitor(company_id):
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "竞品名称不能为空"}), 400
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO competitors (company_id, competitor_name, competitor_domain, geo_score, source_count, ai_accuracy, notes) VALUES (?,?,?,?,?,?,?)",
        (company_id, name, data.get("domain", ""), data.get("geo_score", 0),
         data.get("source_count", 0), data.get("ai_accuracy", 0), data.get("notes", "")),
    )
    comp_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"success": True, "id": comp_id})


@app.route("/api/competitors/<int:comp_id>", methods=["PUT"])
def update_competitor(comp_id):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    fields = []
    values = []
    for col in ("competitor_name", "competitor_domain", "geo_score", "source_count", "ai_accuracy", "notes"):
        if col in data:
            fields.append(f"{col}=?")
            values.append(data[col])
    if not fields:
        return jsonify({"error": "无更新字段"}), 400
    values.append(comp_id)
    conn.execute(f"UPDATE competitors SET {', '.join(fields)} WHERE id=?", values)
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/competitors/<int:comp_id>", methods=["DELETE"])
def delete_competitor(comp_id):
    conn = get_db()
    conn.execute("DELETE FROM competitors WHERE id=?", (comp_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/competitors/compare/<int:company_id>", methods=["GET"])
def compare_competitors(company_id):
    """声音份额+引用差距分析"""
    conn = get_db()
    try:
        company = conn.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
        if not company:
            return jsonify({"error": "公司不存在"}), 404
        competitors = conn.execute(
            "SELECT * FROM competitors WHERE company_id=? ORDER BY geo_score DESC",
            (company_id,),
        ).fetchall()

        all_entities = [{"name": company["name"], "geo_score": company["geo_score"] or 0, "is_self": True}]
        for c in competitors:
            all_entities.append({
                "name": c["competitor_name"],
                "geo_score": c["geo_score"] or 0,
                "source_count": c["source_count"] or 0,
                "ai_accuracy": c["ai_accuracy"] or 0,
                "is_self": False,
            })

        total_score = sum(e["geo_score"] for e in all_entities) or 1
        for e in all_entities:
            e["share_of_voice"] = round(e["geo_score"] / total_score * 100, 1)

        my_score = company["geo_score"] or 0
        for e in all_entities:
            e["citation_gap"] = e["geo_score"] - my_score if not e["is_self"] else 0

        avg_comp_score = (
            sum(e["geo_score"] for e in all_entities if not e["is_self"]) / max(len([e for e in all_entities if not e["is_self"]]), 1)
        ) if len(all_entities) > 1 else 0
        my_rank = sum(1 for e in all_entities if e["geo_score"] > my_score) + 1
    finally:
        conn.close()

    return jsonify({
        "success": True,
        "entities": all_entities,
        "my_score": my_score,
        "avg_competitor_score": round(avg_comp_score, 1),
        "my_rank": my_rank,
        "total_entities": len(all_entities),
    })


# ========== GEO报告 ==========

@app.route("/api/companies/<int:cid>/report", methods=["GET"])
def get_report(cid):
    conn = get_db()
    report = conn.execute("SELECT * FROM geo_reports WHERE company_id=? ORDER BY created_at DESC LIMIT 1", (cid,)).fetchone()
    if not report:
        conn.close()
        return jsonify({"error": "no report"}), 404

    metrics = conn.execute("SELECT * FROM geo_metrics WHERE company_id=? ORDER BY id", (cid,)).fetchall()
    issues = conn.execute("SELECT * FROM website_issues WHERE company_id=? ORDER BY severity, id", (cid,)).fetchall()
    competitors = conn.execute("SELECT * FROM competitors WHERE company_id=?", (cid,)).fetchall()
    tasks = conn.execute("SELECT * FROM optimization_tasks WHERE company_id=? ORDER BY roi_score DESC", (cid,)).fetchall()
    conn.close()

    return jsonify({
        "report": dict(report),
        "metrics": [dict(m) for m in metrics],
        "issues": [dict(i) for i in issues],
        "competitors": [dict(c) for c in competitors],
        "tasks": [dict(t) for t in tasks],
    })


# ========== 案例效果 ==========

@app.route("/api/cases", methods=["GET"])
def list_cases():
    """返回含优化前后对比的案例（基于diagnose_after报告）"""
    conn = get_db()
    rows = conn.execute(
        """SELECT r.id, c.name AS company_name, c.domain, r.score, r.grade,
                  r.summary, r.core_advantage, r.raw_data, r.created_at
           FROM geo_reports r JOIN companies c ON r.company_id = c.id
           WHERE r.report_type = 'diagnose_after'
           ORDER BY r.created_at DESC"""
    ).fetchall()
    conn.close()

    cases = []
    for row in rows:
        d = dict(row)
        before_after = None
        try:
            if d.get("raw_data"):
                raw = json.loads(d["raw_data"])
                before_after = raw.get("before", {}), raw.get("after", {}), raw.get("git", {})
        except (json.JSONDecodeError, AttributeError):
            before_after = None
        d["before_after"] = before_after
        cases.append(d)
    return jsonify(cases)


# ========== Agent ==========

@app.route("/api/agents/<name>", methods=["POST"])
def run_agent(name):
    agent = get_agent(name)
    if not agent:
        return jsonify({"error": f"unknown agent: {name}"}), 404
    data = request.get_json(silent=True) or {}
    result = agent.execute(data)
    return jsonify(result)


# ========== 诊断 ==========

@app.route("/api/diagnose", methods=["POST"])
def diagnose():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "")
    source_dir = data.get("source_dir", "")
    if not url and not source_dir:
        return jsonify({"error": "缺少url或source_dir参数"}), 400
    agent = get_agent("page_diagnoser")
    return jsonify(agent.execute(data))


# ========== AI监控 ==========

@app.route("/api/monitor", methods=["POST"])
def monitor():
    """同步监控（保留兼容，耗时较长；前端请用 /api/monitor/start 异步模式）"""
    data = request.get_json(silent=True) or {}
    company = data.get("company", "")
    if not company:
        return jsonify({"error": "缺少company参数"}), 400
    agent = get_agent("ai_monitor")
    return jsonify(agent.execute({
        "action": "monitor",
        "company": company,
        "keywords": data.get("keywords") or [],
        "industry": data.get("industry", ""),
        "city": data.get("city", ""),
        "brand_keywords": data.get("brand_keywords") or [],
    }))


@app.route("/api/monitor/start", methods=["POST"])
def monitor_start():
    """异步启动AI监控，立即返回task_id（5模型并行，前端轮询status）"""
    from agents.ai_monitor import start_monitor_async
    data = request.get_json(silent=True) or {}
    company = data.get("company", "")
    if not company:
        return jsonify({"error": "缺少company参数"}), 400
    task_id = start_monitor_async(
        company,
        keywords=data.get("keywords") or None,
        brand_keywords=data.get("brand_keywords") or None,
        industry=data.get("industry", ""),
        city=data.get("city", ""),
    )
    return jsonify({"success": True, "task_id": task_id})


@app.route("/api/monitor/status/<task_id>", methods=["GET"])
def monitor_status(task_id):
    from agents.ai_monitor import get_monitor_status
    result = get_monitor_status(task_id)
    # 找到任务时返回体含status键；未找到时只有error键，用status存在性区分
    if "status" not in result:
        return jsonify(result), 404
    return jsonify({"success": True, "data": result})


# ========== 网站优化 ==========

@app.route("/api/optimize", methods=["POST"])
def optimize():
    data = request.get_json(silent=True) or {}
    if not data.get("action"):
        data["action"] = "generate_all"
    agent = get_agent("site_optimizer")
    return jsonify(agent.execute(data))


# ========== 内容生成 ==========

@app.route("/api/content/generate", methods=["POST"])
def generate_content():
    data = request.get_json(silent=True) or {}
    agent = get_agent("content_generator")
    return jsonify(agent.execute(data))


# ========== 优化任务 ==========

@app.route("/api/companies/<int:cid>/tasks", methods=["GET"])
def list_tasks(cid):
    conn = get_db()
    rows = conn.execute("SELECT * FROM optimization_tasks WHERE company_id=? ORDER BY roi_score DESC", (cid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/companies/<int:cid>/tasks/<int:tid>", methods=["PATCH"])
def update_task(cid, tid):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if not status:
        return jsonify({"error": "缺少status参数"}), 400
    conn = get_db()
    conn.execute("UPDATE optimization_tasks SET status=? WHERE id=? AND company_id=?", (status, tid, cid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ========== 多模型探针 ==========

@app.route("/api/probe", methods=["POST"])
def probe():
    data = request.get_json(silent=True) or {}
    company = data.get("company", "")
    if not company:
        return jsonify({"error": "缺少company参数"}), 400
    agent = get_agent("report_generator")
    return jsonify(agent.execute({"action": "probe", "company": company}))


# ========== 深度合成报告 ==========

@app.route("/api/synthesize", methods=["POST"])
def synthesize():
    data = request.get_json(silent=True) or {}
    company = data.get("company", "")
    if not company:
        return jsonify({"error": "缺少company参数"}), 400
    agent = get_agent("report_generator")
    return jsonify(agent.execute({"action": "synthesize", "company": company, "company_id": data.get("company_id"), "probe_data": data.get("probe_data")}))


# ========== 30/60/90天行动计划 ==========

@app.route("/api/action-plan", methods=["POST"])
def action_plan():
    data = request.get_json(silent=True) or {}
    company = data.get("company", "")
    if not company:
        return jsonify({"error": "缺少company参数"}), 400
    agent = get_agent("report_generator")
    return jsonify(agent.execute({"action": "action_plan", "company": company, "company_id": data.get("company_id"), "diagnose_data": data.get("diagnose_data")}))


# ========== 完整报告 ==========

@app.route("/api/full-report", methods=["POST"])
def full_report():
    data = request.get_json(silent=True) or {}
    company = data.get("company", "")
    company_id = data.get("company_id")
    if not company and not company_id:
        return jsonify({"error": "缺少company或company_id参数"}), 400
    if not company:
        conn = get_db()
        row = conn.execute("SELECT name FROM companies WHERE id=?", (company_id,)).fetchone()
        conn.close()
        if not row:
            return jsonify({"error": "公司不存在"}), 404
        company = row["name"]
    agent = get_agent("report_generator")
    return jsonify(agent.execute({"action": "full_report", "company": company, "company_id": company_id}))


# ========== PDF报告导出 ==========

@app.route("/api/report-pdf/<int:cid>", methods=["GET"])
def report_pdf(cid):
    conn = get_db()
    company = conn.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    if not company:
        conn.close()
        return jsonify({"error": "公司不存在"}), 404

    report = conn.execute("SELECT * FROM geo_reports WHERE company_id=? ORDER BY created_at DESC LIMIT 1", (cid,)).fetchone()
    metrics = conn.execute("SELECT * FROM geo_metrics WHERE company_id=?", (cid,)).fetchall()
    issues = conn.execute("SELECT * FROM website_issues WHERE company_id=? ORDER BY severity", (cid,)).fetchall()
    competitors = conn.execute("SELECT * FROM competitors WHERE company_id=?", (cid,)).fetchall()
    tasks = conn.execute("SELECT * FROM optimization_tasks WHERE company_id=? ORDER BY roi_score DESC", (cid,)).fetchall()
    conn.close()

    report_data = {
        "company": dict(company),
        "report": dict(report) if report else {},
        "metrics": [dict(m) for m in metrics],
        "issues": [dict(i) for i in issues],
        "competitors": [dict(c) for c in competitors],
        "tasks": [dict(t) for t in tasks],
    }

    html = generate_report_html(report_data)
    return Response(html, mimetype="text/html; charset=utf-8")


@app.route("/api/report-history/<int:company_id>", methods=["GET"])
def report_history(company_id):
    """报告历史列表"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, company_id, score, grade, created_at FROM geo_reports WHERE company_id=? ORDER BY created_at DESC LIMIT 50",
            (company_id,),
        ).fetchall()
    finally:
        conn.close()
    return jsonify({"success": True, "data": [dict(r) for r in rows]})


@app.route("/api/dashboard/<int:company_id>", methods=["GET"])
def executive_dashboard(company_id):
    """执行仪表板：汇总关键指标"""
    conn = get_db()
    try:
        company = conn.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
        if not company:
            return jsonify({"error": "公司不存在"}), 404

        latest_report = conn.execute(
            "SELECT * FROM geo_reports WHERE company_id=? ORDER BY created_at DESC LIMIT 1",
            (company_id,),
        ).fetchone()

        latest_snapshot = conn.execute(
            "SELECT * FROM monitor_snapshots WHERE company_id=? ORDER BY created_at DESC LIMIT 1",
            (company_id,),
        ).fetchone()

        competitor_count = conn.execute(
            "SELECT COUNT(*) FROM competitors WHERE company_id=?",
            (company_id,),
        ).fetchone()[0]

        task_count = conn.execute(
            "SELECT COUNT(*) FROM optimization_tasks WHERE company_id=?",
            (company_id,),
        ).fetchone()[0]

        snapshot_count = conn.execute(
            "SELECT COUNT(*) FROM monitor_snapshots WHERE company_id=?",
            (company_id,),
        ).fetchone()[0]

        trend = conn.execute(
            "SELECT display_rate, accuracy_score, created_at FROM monitor_snapshots WHERE company_id=? ORDER BY created_at DESC LIMIT 7",
            (company_id,),
        ).fetchall()
    finally:
        conn.close()

    return jsonify({
        "success": True,
        "company": dict(company),
        "geo_score": company["geo_score"] or 0,
        "geo_grade": company["geo_grade"] or "D",
        "report_score": latest_report["score"] if latest_report else None,
        "report_grade": latest_report["grade"] if latest_report else None,
        "display_rate": latest_snapshot["display_rate"] if latest_snapshot else None,
        "accuracy_score": latest_snapshot["accuracy_score"] if latest_snapshot else None,
        "competitor_count": competitor_count,
        "task_count": task_count,
        "snapshot_count": snapshot_count,
        "trend": [dict(r) for r in reversed(trend)],
    })


@app.route("/api/report-csv/<int:company_id>", methods=["GET"])
def report_csv(company_id):
    """导出监控历史为CSV"""
    import csv
    import io
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT created_at, display_rate, accuracy_score, mention_count, total_queries, snapshot_type FROM monitor_snapshots WHERE company_id=? ORDER BY created_at DESC",
            (company_id,),
        ).fetchall()
    finally:
        conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["时间", "展示率(%)", "准确率(%)", "提及次数", "总查询数", "类型"])
    for r in rows:
        writer.writerow([r["created_at"], r["display_rate"], r["accuracy_score"], r["mention_count"], r["total_queries"], r["snapshot_type"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=monitor_history_{company_id}.csv"},
    )


# ========== 拓词 ==========

# ========== 订阅计费 ==========

PLANS_INFO = [
    {"id": "free", "name": "免费版", "price": 0, "period": "月",
     "limits": {"companies": 1, "monitors_per_month": 10, "reports_per_month": 3},
     "features": ["1个企业", "每月10次AI监控", "每月3份报告", "基础诊断", "SHEEP评分"]},
    {"id": "pro", "name": "专业版", "price": 999, "period": "年",
     "limits": {"companies": 10, "monitors_per_month": 100, "reports_per_month": 50},
     "features": ["10个企业", "每月100次AI监控", "每月50份报告", "竞品追踪", "定时监控", "CSV导出", "优先支持"]},
    {"id": "enterprise", "name": "企业版", "price": 2999, "period": "年",
     "limits": {"companies": 999, "monitors_per_month": 9999, "reports_per_month": 9999},
     "features": ["不限企业数", "无限AI监控", "无限报告", "API接入", "定制策略", "专属客服", "白标报告"]},
]


@app.route("/api/billing/plans", methods=["GET"])
def billing_plans():
    return jsonify({"success": True, "data": PLANS_INFO})


@app.route("/api/billing/usage", methods=["GET"])
def billing_usage():
    user = getattr(g, "current_user", None)
    if not user:
        return jsonify({"error": "未登录"}), 401
    user_id = user["user_id"]
    user_info = get_user(user_id)
    if not user_info:
        return jsonify({"error": "用户不存在"}), 404

    plan = user_info.get("plan", "free")
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    conn = get_db()
    try:
        company_count = conn.execute("SELECT COUNT(*) FROM companies WHERE owner_id=?", (user_id,)).fetchone()[0]
        monitor_count = conn.execute(
            "SELECT COUNT(*) FROM monitor_snapshots ms JOIN companies c ON ms.company_id=c.id "
            "WHERE c.owner_id=? AND ms.created_at >= date('now','-30 days')",
            (user_id,),
        ).fetchone()[0]
        report_count = conn.execute(
            "SELECT COUNT(*) FROM geo_reports r JOIN companies c ON r.company_id=c.id "
            "WHERE c.owner_id=? AND r.created_at >= date('now','-30 days')",
            (user_id,),
        ).fetchone()[0]
    finally:
        conn.close()

    return jsonify({
        "success": True,
        "plan": plan,
        "plan_name": {"free": "免费版", "pro": "专业版", "enterprise": "企业版"}.get(plan, plan),
        "usage": {
            "companies": {"used": company_count, "limit": limits["companies"]},
            "monitors_per_month": {"used": monitor_count, "limit": limits["monitors_per_month"]},
            "reports_per_month": {"used": report_count, "limit": limits["reports_per_month"]},
        },
    })


@app.route("/api/billing/upgrade", methods=["POST"])
def billing_upgrade():
    user = getattr(g, "current_user", None)
    if not user:
        return jsonify({"error": "未登录"}), 401
    data = request.get_json(silent=True) or {}
    new_plan = data.get("plan", "")
    if new_plan not in ("free", "pro", "enterprise"):
        return jsonify({"error": "无效的套餐"}), 400

    conn = get_db()
    try:
        conn.execute("UPDATE users SET plan=? WHERE id=?", (new_plan, user["user_id"]))
        conn.commit()
    finally:
        conn.close()

    token = create_token(user["user_id"], user["email"], new_plan)
    return jsonify({
        "success": True,
        "plan": new_plan,
        "token": token,
        "message": f"已升级至{ {'free': '免费版', 'pro': '专业版', 'enterprise': '企业版'}.get(new_plan, new_plan) }",
    })


# ========== 拓词 ==========

@app.route("/api/keywords/expand", methods=["POST"])
def keywords_expand():
    data = request.get_json(silent=True) or {}
    company_id = data.get("company_id")
    seed = data.get("seed_keyword", "")
    if not company_id or not seed:
        return jsonify({"error": "缺少company_id或seed_keyword"}), 400
    conn = get_db()
    row = conn.execute("SELECT name, industry FROM companies WHERE id=?", (company_id,)).fetchone()
    conn.close()
    company_name = row["name"] if row else ""
    industry = row["industry"] if row else ""
    result = expand_keywords(company_id, seed, company_name, industry)
    return jsonify({"success": True, "data": result})


@app.route("/api/keywords/list/<int:company_id>", methods=["GET"])
def keywords_list(company_id):
    seed = request.args.get("seed")
    rows = get_expanded_keywords(company_id, seed)
    return jsonify({"success": True, "data": rows})


# ========== 定时监控 ==========

@app.route("/api/monitor/snapshot", methods=["POST"])
def monitor_snapshot():
    """同步快照（保留兼容，耗时长；前端请用 snapshot/start 异步模式）"""
    data = request.get_json(silent=True) or {}
    company_id = data.get("company_id")
    if not company_id:
        return jsonify({"error": "缺少company_id"}), 400
    result = _take_snapshot(company_id)
    return jsonify({"success": True, "data": result})


@app.route("/api/monitor/snapshot/start", methods=["POST"])
def monitor_snapshot_start():
    """异步启动快照，立即返回task_id"""
    from agents.scheduler import start_snapshot_async
    data = request.get_json(silent=True) or {}
    company_id = data.get("company_id")
    if not company_id:
        return jsonify({"error": "缺少company_id"}), 400
    task_id = start_snapshot_async(company_id)
    return jsonify({"success": True, "task_id": task_id})


@app.route("/api/monitor/snapshot/status/<task_id>", methods=["GET"])
def monitor_snapshot_status(task_id):
    from agents.scheduler import get_snapshot_status
    result = get_snapshot_status(task_id)
    # 同monitor_status：用status键存在性区分找到/未找到
    if "status" not in result:
        return jsonify(result), 404
    return jsonify({"success": True, "data": result})


@app.route("/api/monitor/trend/<int:company_id>", methods=["GET"])
def monitor_trend(company_id):
    limit = request.args.get("limit", 30, type=int)
    rows = get_trend_data(company_id, limit)
    return jsonify({"success": True, "data": rows})


@app.route("/api/monitor/history/<int:company_id>", methods=["GET"])
def monitor_history(company_id):
    """获取监控历史记录列表"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    offset = (page - 1) * per_page
    conn = get_db()
    try:
        total = conn.execute("SELECT COUNT(*) FROM monitor_snapshots WHERE company_id=?", (company_id,)).fetchone()[0]
        rows = conn.execute(
            "SELECT id, company_id, snapshot_type, total_queries, mention_count, display_rate, accuracy_score, created_at FROM monitor_snapshots WHERE company_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (company_id, per_page, offset),
        ).fetchall()
    finally:
        conn.close()
    return jsonify({
        "success": True,
        "data": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@app.route("/api/monitor/visibility-score/<int:company_id>", methods=["GET"])
def visibility_score(company_id):
    """计算综合可见性评分（0-100）"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM monitor_snapshots WHERE company_id=? ORDER BY created_at DESC LIMIT 1",
            (company_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return jsonify({"success": True, "score": None, "grade": None})

    display_rate = row["display_rate"] or 0
    accuracy = row["accuracy_score"] or 0
    detail = json.loads(row["detail_json"]) if row["detail_json"] else {}
    negative_rate = 0
    if isinstance(detail, list):
        neg_count = sum(1 for r in detail if r.get("negative_mention"))
        negative_rate = (neg_count / len(detail) * 100) if detail else 0

    # 综合评分 = 展示率×0.5 + 准确率×0.3 + (100-负面率)×0.2
    score = round(display_rate * 0.5 + accuracy * 0.3 + (100 - negative_rate) * 0.2)
    if score >= 80:
        grade = "A"
    elif score >= 70:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"

    return jsonify({
        "success": True,
        "score": score,
        "grade": grade,
        "display_rate": display_rate,
        "accuracy": accuracy,
        "negative_rate": round(negative_rate, 1),
        "snapshot_id": row["id"],
        "created_at": row["created_at"],
    })


@app.route("/api/scheduler/jobs", methods=["GET"])
def scheduler_jobs_list():
    company_id = request.args.get("company_id", type=int)
    jobs = get_scheduled_jobs(company_id)
    return jsonify({"success": True, "data": jobs})


@app.route("/api/scheduler/jobs", methods=["POST"])
def scheduler_jobs_create():
    data = request.get_json(silent=True) or {}
    company_id = data.get("company_id")
    job_type = data.get("job_type", "monitor")
    cron_expr = data.get("cron_expr", "0 9 * * *")
    if not company_id:
        return jsonify({"error": "缺少company_id"}), 400
    job = create_scheduled_job(company_id, job_type, cron_expr)
    reload_scheduler()
    return jsonify({"success": True, "data": job})


@app.route("/api/scheduler/jobs/<int:job_id>", methods=["PATCH"])
def scheduler_jobs_toggle(job_id):
    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled", True)
    toggle_scheduled_job(job_id, enabled)
    reload_scheduler()
    return jsonify({"success": True})


@app.route("/api/scheduler/jobs/<int:job_id>", methods=["DELETE"])
def scheduler_jobs_delete(job_id):
    delete_scheduled_job(job_id)
    reload_scheduler()
    return jsonify({"success": True})


# ========== GEO基准测试 ==========

@app.route("/api/benchmark", methods=["POST"])
def benchmark():
    data = request.get_json(silent=True) or {}
    company_name = data.get("company_name", "")
    industry = data.get("industry", "")
    queries = data.get("queries")
    models = data.get("models")
    if not company_name:
        company_id = data.get("company_id")
        if company_id:
            conn = get_db()
            row = conn.execute("SELECT name, industry FROM companies WHERE id=?", (company_id,)).fetchone()
            conn.close()
            if row:
                company_name = row["name"]
                industry = row["industry"]
        if not company_name:
            return jsonify({"error": "缺少company_name或company_id"}), 400
    result = run_benchmark(company_name, industry, queries, models)
    return jsonify({"success": True, "data": result})


@app.route("/api/benchmark/start", methods=["POST"])
def benchmark_start():
    """异步启动基准测试，返回task_id"""
    import threading, uuid
    from agents.geo_benchmark import _run_benchmark_with_progress, _TaskStore

    data = request.get_json(silent=True) or {}
    company_name = data.get("company_name", "")
    industry = data.get("industry", "")
    queries = data.get("queries")
    models = data.get("models")
    if not company_name:
        company_id = data.get("company_id")
        if company_id:
            conn = get_db()
            row = conn.execute("SELECT name, industry FROM companies WHERE id=?", (company_id,)).fetchone()
            conn.close()
            if row:
                company_name = row["name"]
                industry = row["industry"]
        if not company_name:
            return jsonify({"error": "缺少company_name或company_id"}), 400

    task_id = str(uuid.uuid4())[:8]
    total_queries = len(queries) if queries else 3
    total_models = len(models) if models else 3
    total_steps = total_queries * total_models * 2

    _BENCHMARK_TASKS[task_id] = {
        "status": "running",
        "progress": 0,
        "total_steps": total_steps,
        "current_step": 0,
        "current_desc": "",
        "result": None,
        "error": None,
    }

    def _worker():
        try:
            result = _run_benchmark_with_progress(
                task_id, company_name, industry, queries, models, _BENCHMARK_TASKS
            )
            _BENCHMARK_TASKS[task_id]["result"] = result
            _BENCHMARK_TASKS[task_id]["status"] = "done"
            _BENCHMARK_TASKS[task_id]["progress"] = 100
        except Exception as e:
            _BENCHMARK_TASKS[task_id]["error"] = str(e)
            _BENCHMARK_TASKS[task_id]["status"] = "failed"

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return jsonify({"success": True, "task_id": task_id})


@app.route("/api/benchmark/status/<task_id>", methods=["GET"])
def benchmark_status(task_id):
    task = _BENCHMARK_TASKS.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在", "task_id": task_id, "known": list(_BENCHMARK_TASKS.keys())}), 404
    return jsonify({"success": True, "data": {
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "current_step": task["current_step"],
        "total_steps": task["total_steps"],
        "current_desc": task["current_desc"],
        "result": task["result"],
        "error": task["error"],
    }})


# ========== SHEEP GEM评分 ==========

@app.route("/api/sheep-score", methods=["POST"])
def sheep_score():
    data = request.get_json(silent=True) or {}
    company_name = data.get("company_name", "")
    industry = data.get("industry", "")
    url = data.get("url", "")
    evidence = data.get("evidence", {})
    auto_diagnose = data.get("auto_diagnose", False)

    if not company_name:
        company_id = data.get("company_id")
        if company_id:
            conn = get_db()
            row = conn.execute("SELECT name, industry, website FROM companies WHERE id=?", (company_id,)).fetchone()
            conn.close()
            if row:
                company_name = row["name"]
                industry = row["industry"]
                url = url or row["website"]
        if not company_name:
            return jsonify({"error": "缺少company_name或company_id"}), 400

    # 如果开启自动诊断且有URL，先诊断网站再构建evidence
    diagnosis_result = None
    if auto_diagnose and url:
        try:
            agent = get_agent("page_diagnoser")
            diag_resp = agent.execute({"url": url, "verify_ssl": bool(data.get("verify_ssl", True))})
            if diag_resp.get("success"):
                diagnosis_result = diag_resp.get("data", {})
                evidence = build_evidence_from_diagnosis(diagnosis_result)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("网站诊断失败: %s", e)

    result = calculate_gem_score(company_name, industry, url, evidence, diagnosis=diagnosis_result)
    if diagnosis_result:
        result["diagnosis"] = {
            "url": url,
            "overall_score": diagnosis_result.get("score", 0),
            "status_code": diagnosis_result.get("status_code", 0),
        }
    result["evidence_source"] = "auto_diagnosis" if (auto_diagnose and evidence) else "manual"
    return jsonify({"success": True, "data": result})


@app.route("/api/sheep/model-weights", methods=["GET"])
def model_weights():
    return jsonify({"success": True, "data": get_cn_model_weights()})


# ========== GEO内容优化策略 ==========

@app.route("/api/content-strategies", methods=["GET"])
def list_strategies():
    return jsonify({"success": True, "data": get_strategies_info()})


@app.route("/api/content-strategies/apply", methods=["POST"])
def apply_content_strategy():
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    strategy = data.get("strategy")
    selected = data.get("selected")
    if not content:
        return jsonify({"error": "缺少content"}), 400
    if strategy:
        result = apply_strategy(content, strategy)
    else:
        result = apply_all_strategies(content, selected=selected)
    return jsonify({"success": True, "data": result})


# ========== 内容合规检测 ==========

@app.route("/api/compliance/rules", methods=["GET"])
def compliance_rules():
    return jsonify({"success": True, "data": get_compliance_rules()})


@app.route("/api/compliance/check", methods=["POST"])
def compliance_check():
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    keywords = data.get("keywords")
    if not content:
        return jsonify({"error": "缺少content"}), 400
    if keywords is not None and not isinstance(keywords, list):
        return jsonify({"error": "keywords必须是字符串数组"}), 400
    result = check_compliance(content, keywords)
    return jsonify({"success": True, "data": result})


# ========== 公司入库 ==========

@app.route("/api/company/ingest", methods=["POST"])
def company_ingest():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "")
    company_name = data.get("company_name", "")
    if not url:
        return jsonify({"error": "缺少url参数"}), 400
    try:
        result = ingest_company_website(url, company_name)
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"入库失败: {e}"}), 500


# ========== RAG问答 ==========

@app.route("/api/chat/channels", methods=["GET"])
def chat_channels():
    return jsonify({"success": True, "data": get_channels()})


@app.route("/api/chat/conversations/<int:company_id>", methods=["GET"])
def chat_conversations(company_id):
    channel = request.args.get("channel")
    rows = get_conversations(company_id, channel)
    return jsonify({"success": True, "data": rows})


@app.route("/api/chat", methods=["POST"])
def chat_send():
    data = request.get_json(silent=True) or {}
    company_id = data.get("company_id")
    question = data.get("question", "")
    channel = data.get("channel", "geo_basic")
    model = data.get("model")
    if not company_id or not question:
        return jsonify({"error": "缺少company_id或question"}), 400
    result = chat(company_id, question, channel, model)
    return jsonify({"success": True, "data": result})


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream_route():
    data = request.get_json(silent=True) or {}
    company_id = data.get("company_id")
    question = data.get("question", "")
    channel = data.get("channel", "geo_basic")
    model = data.get("model")
    if not company_id or not question:
        return jsonify({"error": "缺少company_id或question"}), 400
    return Response(
        chat_stream(company_id, question, channel, model),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ========== GDO决策背书层 ==========

@app.route("/api/gdo/dimensions", methods=["GET"])
def gdo_dimensions():
    return jsonify({"success": True, "data": get_gdo_dimensions()})


@app.route("/api/gdo/audit", methods=["POST"])
def gdo_audit():
    data = request.get_json(silent=True) or {}
    company_name = data.get("company_name", "")
    domain = data.get("domain", "")
    industry = data.get("industry", "")
    diagnosis_data = data.get("diagnosis_data")
    keywords = data.get("keywords")
    benchmark_data = data.get("benchmark_data")
    model = data.get("model")
    if not company_name or not domain:
        return jsonify({"error": "缺少company_name或domain"}), 400
    result = audit_decision_evidence(company_name, domain, industry, diagnosis_data, keywords, benchmark_data, model)
    return jsonify({"success": True, "data": result})


@app.route("/api/gdo/simulate", methods=["POST"])
def gdo_simulate():
    data = request.get_json(silent=True) or {}
    company_name = data.get("company_name", "")
    domain = data.get("domain", "")
    competitor = data.get("competitor", "")
    model = data.get("model")
    if not company_name or not domain:
        return jsonify({"error": "缺少company_name或domain"}), 400
    result = simulate_ai_decision_query(company_name, domain, competitor, model)
    return jsonify({"success": True, "data": result})


# ========== AI决策对比测试 ==========

@app.route("/api/decision-test/scenarios", methods=["GET"])
def decision_scenarios():
    return jsonify({"success": True, "data": get_decision_scenarios()})


@app.route("/api/decision-test", methods=["POST"])
def decision_test():
    data = request.get_json(silent=True) or {}
    company_name = data.get("company_name", "")
    domain = data.get("domain", "")
    competitor = data.get("competitor", "")
    scenarios = data.get("scenarios")
    model = data.get("model")
    if not company_name or not domain:
        return jsonify({"error": "缺少company_name或domain"}), 400
    result = run_decision_test(company_name, domain, competitor, scenarios, model)
    return jsonify({"success": True, "data": result})


# ========== 六层成熟度评分 ==========

@app.route("/api/maturity/layers", methods=["GET"])
def maturity_layers():
    return jsonify({"success": True, "data": get_maturity_layers()})


@app.route("/api/maturity/score", methods=["POST"])
def maturity_score():
    data = request.get_json(silent=True) or {}
    result = calculate_maturity(
        diagnosis=data.get("diagnosis"),
        benchmark=data.get("benchmark"),
        sheep=data.get("sheep"),
        gdo=data.get("gdo"),
        keywords_count=data.get("keywords_count", 0),
        strategies_count=data.get("strategies_count", 0),
    )
    return jsonify({"success": True, "data": result})


# ========== GEO A/B测试 ==========

@app.route("/api/geo-abtest/suites", methods=["GET"])
def abtest_suites():
    company_id = request.args.get("company_id", type=int)
    rows = get_test_suites(company_id)
    return jsonify({"success": True, "data": rows})


@app.route("/api/geo-abtest/create", methods=["POST"])
def abtest_create():
    data = request.get_json(silent=True) or {}
    company_id = data.get("company_id", 1)
    name = data.get("name", "")
    questions = data.get("questions", [])
    platforms = data.get("platforms")
    if not name or not questions:
        return jsonify({"error": "缺少name或questions"}), 400
    result = create_test_suite(company_id, name, questions, platforms)
    return jsonify({"success": True, "data": result})


@app.route("/api/geo-abtest/run/<int:test_id>", methods=["POST"])
def abtest_run(test_id):
    data = request.get_json(silent=True) or {}
    company_name = data.get("company_name", "")
    company_domain = data.get("company_domain", "")
    brand_aliases = data.get("brand_aliases")
    phase = data.get("phase", "before")
    if not company_name:
        return jsonify({"error": "缺少company_name"}), 400
    result = run_test_batch(test_id, company_name, company_domain, brand_aliases, phase)
    return jsonify({"success": True, "data": result})


@app.route("/api/geo-abtest/compare/<int:test_id>", methods=["GET"])
def abtest_compare(test_id):
    result = compare_phases(test_id)
    return jsonify({"success": True, "data": result})


@app.route("/api/geo-abtest/page-types", methods=["GET"])
def abtest_page_types():
    return jsonify({"success": True, "data": get_page_types()})


@app.route("/api/geo-abtest/sources", methods=["GET"])
def abtest_sources():
    return jsonify({"success": True, "data": get_source_categories()})


# ========== PDF去重审计 ==========

@app.route("/api/pdf-dedup/audit", methods=["POST"])
def pdf_dedup_audit():
    data = request.get_json(silent=True) or {}
    domain = data.get("domain", "")
    urls = data.get("urls")
    if not domain and not urls:
        return jsonify({"error": "缺少domain或urls"}), 400
    if urls:
        result = audit_duplicate_pdfs(urls)
    else:
        result = audit_website_pdfs(domain)
    return jsonify({"success": True, "data": result})


def _bootstrap():
    """初始化DB/种子数据/定时任务。幂等，模块导入时执行一次。

    gunicorn 不走 __main__ 块，若只在 __main__ 初始化，
    生产环境会出现表未创建（/api/companies 500: no such table）。
    注意: init_scheduler 无多worker守卫，须配合单worker部署(见Dockerfile)。
    """
    init_db()
    seed_mzy_data()
    init_scheduler(app)


_bootstrap()


if __name__ == "__main__":
    print(f"[INFO] GEO Platform 启动: http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
