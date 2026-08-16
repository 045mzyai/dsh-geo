"""定时监控Agent — APScheduler定期查询AI引用率变化趋势"""

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime

import requests
from config import DB_PATH, MZY_API_KEY, MZY_BASE_URL, DEFAULT_MODEL

logger = logging.getLogger(__name__)

MODEL_TEMPS = {"kimi-k3": 1.0}
PROBE_MODELS = ["deepseek-v4-pro", "kimi-k3", "glm-5.2", "minimax-m3", "hy3"]

MONITOR_QUERIES = [
    "请推荐一家{industry}公司",
    "{company_name}怎么样",
    "{industry}哪家公司服务好",
    "推荐{city}的{industry}服务商",
]

MONITOR_PROMPT = """判断以下AI回答中是否提到了目标公司。

目标公司：{company_name}
行业：{industry}
用户问题：{query}
AI回答：{answer}

返回JSON：
{{"mentioned": true/false, "accuracy": 0.0-1.0, "position": "first/middle/last/none"}}"""


def _call_llm(prompt: str, model: str = None, temperature: float = None, json_mode: bool = False) -> str:
    model = model or DEFAULT_MODEL
    temp = temperature if temperature is not None else MODEL_TEMPS.get(model, 0.3)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temp,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    resp = requests.post(
        f"{MZY_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {MZY_API_KEY}"},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _probe_one(model_name: str, query: str, company_name: str, industry: str) -> dict:
    """单个(模型,查询)探测：取回答 + LLM裁判判定提及与准确度"""
    answer = _call_llm(query, model=model_name, temperature=MODEL_TEMPS.get(model_name, 0.3))
    judge_raw = _call_llm(
        MONITOR_PROMPT.format(company_name=company_name, industry=industry, query=query, answer=answer),
        temperature=0.3,
        json_mode=True,
    )
    judge = json.loads(judge_raw)
    return {
        "model": model_name, "query": query,
        "mentioned": judge.get("mentioned", False),
        "accuracy": judge.get("accuracy", 0),
        "position": judge.get("position", "none"),
    }


def _take_snapshot(company_id: int) -> dict:
    """对单个公司执行一次AI引用率快照（模型×查询并行）"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from models import get_company
    company = get_company(company_id)
    if not company:
        return {"error": "公司不存在"}

    company_name = company["name"]
    industry = company.get("industry", "科技")
    city = company.get("city", "成都")

    jobs = [
        (model_name, q_template.format(company_name=company_name, industry=industry, city=city))
        for model_name in PROBE_MODELS
        for q_template in MONITOR_QUERIES
    ]

    results = []
    with ThreadPoolExecutor(max_workers=len(PROBE_MODELS)) as executor:
        futures = {
            executor.submit(_probe_one, model_name, query, company_name, industry): (model_name, query)
            for model_name, query in jobs
        }
        for future in as_completed(futures):
            model_name, query = futures[future]
            try:
                results.append(future.result())
            except Exception as e:
                logger.warning("监控查询失败 model=%s query=%s: %s", model_name, query[:30], e)
                results.append({"model": model_name, "query": query, "error": str(e)})

    total_queries = len(jobs)
    mention_count = sum(1 for r in results if r.get("mentioned"))
    accuracy_sum = sum(r.get("accuracy", 0) for r in results if r.get("mentioned"))

    display_rate = round(mention_count / total_queries, 4) if total_queries > 0 else 0
    avg_accuracy = round(accuracy_sum / mention_count, 4) if mention_count > 0 else 0

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO monitor_snapshots (company_id, snapshot_type, total_queries, mention_count, display_rate, accuracy_score, detail_json) VALUES (?,?,?,?,?,?,?)",
            (company_id, "scheduled", total_queries, mention_count, display_rate, avg_accuracy, json.dumps(results, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "company_id": company_id,
        "total_queries": total_queries,
        "mention_count": mention_count,
        "display_rate": display_rate,
        "accuracy_score": avg_accuracy,
        "timestamp": datetime.now().isoformat(),
    }


# ========== 快照异步任务（手动快照HTTP入口用，避免阻塞请求） ==========

_SNAPSHOT_TASKS = {}
_SNAPSHOT_LOCK = threading.Lock()


def start_snapshot_async(company_id: int) -> str:
    """启动异步快照任务，立即返回task_id"""
    task_id = str(uuid.uuid4())[:8]
    with _SNAPSHOT_LOCK:
        _SNAPSHOT_TASKS[task_id] = {
            "status": "running", "progress": 10,
            "current_desc": f"公司{company_id} AI引用率快照执行中",
            "result": None, "error": None,
        }

    def _worker():
        try:
            result = _take_snapshot(company_id)
            with _SNAPSHOT_LOCK:
                _SNAPSHOT_TASKS[task_id]["result"] = result
                _SNAPSHOT_TASKS[task_id]["status"] = "done"
                _SNAPSHOT_TASKS[task_id]["progress"] = 100
        except Exception as e:
            logger.error("异步快照失败: %s", e, exc_info=True)
            with _SNAPSHOT_LOCK:
                _SNAPSHOT_TASKS[task_id]["error"] = str(e)
                _SNAPSHOT_TASKS[task_id]["status"] = "failed"

    threading.Thread(target=_worker, daemon=True).start()
    return task_id


def get_snapshot_status(task_id: str) -> dict:
    with _SNAPSHOT_LOCK:
        task = _SNAPSHOT_TASKS.get(task_id)
        if not task:
            return {"error": "任务不存在", "known": list(_SNAPSHOT_TASKS.keys())}
        return {"task_id": task_id, **task}


def get_trend_data(company_id: int, limit: int = 30) -> list:
    """获取某公司的引用率趋势数据"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM monitor_snapshots WHERE company_id=? ORDER BY created_at DESC LIMIT ?",
            (company_id, limit),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]
    finally:
        conn.close()


def get_scheduled_jobs(company_id: int = None) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if company_id:
            rows = conn.execute("SELECT * FROM scheduled_jobs WHERE company_id=?", (company_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM scheduled_jobs").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_scheduled_job(company_id: int, job_type: str, cron_expr: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "INSERT INTO scheduled_jobs (company_id, job_type, cron_expr, enabled) VALUES (?,?,?,1)",
            (company_id, job_type, cron_expr),
        )
        conn.commit()
        return {"id": cur.lastrowid, "company_id": company_id, "job_type": job_type, "cron_expr": cron_expr, "enabled": True}
    finally:
        conn.close()


def toggle_scheduled_job(job_id: int, enabled: bool) -> bool:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("UPDATE scheduled_jobs SET enabled=? WHERE id=?", (1 if enabled else 0, job_id))
        conn.commit()
        return True
    finally:
        conn.close()


def delete_scheduled_job(job_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM scheduled_jobs WHERE id=?", (job_id,))
        conn.commit()
        return True
    finally:
        conn.close()


# ── APScheduler 集成 ──

_scheduler = None


def init_scheduler(app):
    """初始化APScheduler，注册定时任务"""
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("apscheduler未安装，定时监控不可用。pip install apscheduler")
        return

    _scheduler = BackgroundScheduler(daemon=True)

    # 加载已注册的定时任务
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        jobs = conn.execute("SELECT * FROM scheduled_jobs WHERE enabled=1").fetchall()
    finally:
        conn.close()

    for job in jobs:
        _add_job_to_scheduler(dict(job))

    _scheduler.start()
    logger.info("APScheduler已启动，已注册%d个定时任务", len(jobs))


def _add_job_to_scheduler(job: dict):
    """将数据库中的job注册到APScheduler"""
    if not _scheduler:
        return
    from apscheduler.triggers.cron import CronTrigger

    job_id = f"monitor_{job['id']}"
    parts = job["cron_expr"].split()
    if len(parts) != 5:
        logger.error("cron表达式格式错误: %s", job["cron_expr"])
        return

    trigger = CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4])

    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)

    _scheduler.add_job(
        _run_scheduled_task,
        trigger=trigger,
        id=job_id,
        args=[job["company_id"], job["job_type"]],
        replace_existing=True,
    )
    logger.info("注册定时任务: %s company=%s cron=%s", job_id, job["company_id"], job["cron_expr"])


def _run_scheduled_task(company_id: int, job_type: str):
    """定时任务执行入口"""
    logger.info("执行定时任务: company=%s type=%s", company_id, job_type)
    try:
        if job_type == "monitor":
            result = _take_snapshot(company_id)
            logger.info("定时监控完成: %s", result)
        elif job_type == "keyword":
            from agents.keyword_expander import expand_keywords
            from models import get_company
            company = get_company(company_id)
            if company:
                expand_keywords(company_id, company["name"], company["name"], company.get("industry", ""))
    except Exception as e:
        logger.error("定时任务执行失败: %s", e, exc_info=True)

    # 更新运行记录
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE scheduled_jobs SET last_run_at=datetime('now','localtime'), run_count=run_count+1 WHERE company_id=? AND job_type=?",
            (company_id, job_type),
        )
        conn.commit()
    finally:
        conn.close()


def reload_scheduler():
    """重新加载所有定时任务（增删改后调用）"""
    if not _scheduler:
        return
    _scheduler.remove_all_jobs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        jobs = conn.execute("SELECT * FROM scheduled_jobs WHERE enabled=1").fetchall()
    finally:
        conn.close()
    for job in jobs:
        _add_job_to_scheduler(dict(job))
    logger.info("APScheduler已重载，%d个活跃任务", len(jobs))
