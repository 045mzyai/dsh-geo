"""RAG问答Agent — 蒸馏自GEORank solutions.py

对话持久化 + 诊断报告上下文注入 + SSE流式输出
"""
from __future__ import annotations
import json
import logging
import sqlite3
from datetime import datetime
from typing import Generator
import requests
from config import MZY_API_KEY, MZY_BASE_URL, DEFAULT_MODEL, DB_PATH

logger = logging.getLogger(__name__)

CHANNELS = {
    "geo_basic": {"name": "GEO基础", "description": "GEO概念、原理、最佳实践"},
    "diagnosis": {"name": "诊断解读", "description": "网站诊断结果解读与建议"},
    "optimization": {"name": "优化策略", "description": "AI搜索优化方案与执行"},
    "benchmark": {"name": "基准测试", "description": "GEO基准测试与竞品对比"},
}

SYSTEM_PROMPT = """你是GEO（生成式引擎优化）专家助手。基于用户的网站诊断报告和GEO知识库回答问题。
规则：
1. 回答简洁专业，直接给出可执行建议
2. 如果提供了诊断报告上下文，优先引用报告中的数据
3. 不确定时明确说明，不编造数据
4. 中文回答"""


def _call_llm_stream(messages: list[dict], model: str = None) -> Generator[str, None, None]:
    model = model or DEFAULT_MODEL
    resp = requests.post(
        f"{MZY_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {MZY_API_KEY}"},
        json={"model": model, "messages": messages, "temperature": 0.5, "stream": True},
        timeout=90,
        stream=True,
    )
    resp.raise_for_status()
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        data = line[6:]
        if data.strip() == "[DONE]":
            break
        try:
            chunk = json.loads(data)
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content")
            if content:
                yield content
        except (json.JSONDecodeError, IndexError, KeyError):
            continue


def _call_llm(messages: list[dict], model: str = None) -> str:
    model = model or DEFAULT_MODEL
    resp = requests.post(
        f"{MZY_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {MZY_API_KEY}"},
        json={"model": model, "messages": messages, "temperature": 0.5},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _build_context(company_id: int, channel: str) -> str:
    parts = []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        company = conn.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
        if company:
            parts.append(f"公司：{company['name']}（{company['domain']}，{company['industry']}）")

        report = conn.execute("SELECT * FROM diagnosis_reports WHERE company_id=? ORDER BY created_at DESC LIMIT 1", (company_id,)).fetchone()
        if report:
            parts.append(f"诊断评分：{report['score']}/100")
            if report.get("issues"):
                try:
                    issues = json.loads(report["issues"])
                    top_issues = [i.get("title", i.get("category", "")) for i in issues[:5] if isinstance(i, dict)]
                    if top_issues:
                        parts.append("主要问题：" + "；".join(top_issues))
                except (json.JSONDecodeError, TypeError):
                    pass

        keywords = conn.execute("SELECT expanded_keyword, dimension FROM keyword_expansions WHERE company_id=? ORDER BY recommendation_score DESC LIMIT 10", (company_id,)).fetchall()
        if keywords:
            kw_text = "；".join([f"{r['expanded_keyword']}({r['dimension']})" for r in keywords])
            parts.append(f"已扩展关键词：{kw_text}")

        snapshots = conn.execute("SELECT * FROM monitor_snapshots WHERE company_id=? ORDER BY created_at DESC LIMIT 3", (company_id,)).fetchall()
        if snapshots:
            latest = snapshots[0]
            parts.append(f"最新监控：展示率{latest['display_rate']*100:.1f}%，准确率{latest['accuracy_score']*100:.1f}%")
    finally:
        conn.close()

    if channel == "geo_basic":
        parts.append("频道：GEO基础问答，解释GEO概念和原理")
    elif channel == "diagnosis":
        parts.append("频道：诊断解读，帮助用户理解网站诊断结果")
    elif channel == "optimization":
        parts.append("频道：优化策略，提供可执行的GEO优化建议")
    elif channel == "benchmark":
        parts.append("频道：基准测试，解读GEO基准测试结果")

    return "\n".join(parts) if parts else "暂无上下文数据"


def get_channels() -> list[dict]:
    return [{"key": k, "name": v["name"], "description": v["description"]} for k, v in CHANNELS.items()]


def get_conversations(company_id: int, channel: str = None, limit: int = 20) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if channel:
            rows = conn.execute(
                "SELECT * FROM chat_conversations WHERE company_id=? AND channel=? ORDER BY created_at DESC LIMIT ?",
                (company_id, channel, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM chat_conversations WHERE company_id=? ORDER BY created_at DESC LIMIT ?",
                (company_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def chat(company_id: int, question: str, channel: str = "geo_basic", model: str = None) -> dict:
    context = _build_context(company_id, channel)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n上下文信息：\n" + context},
        {"role": "user", "content": question},
    ]

    answer = _call_llm(messages, model)

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute(
            "INSERT INTO chat_conversations (company_id, channel, question, answer, model, created_at) VALUES (?,?,?,?,?,?)",
            (company_id, channel, question, answer, model or DEFAULT_MODEL, datetime.now().isoformat()),
        )
        conn.commit()
        conv_id = cursor.lastrowid
    finally:
        conn.close()

    return {"id": conv_id, "question": question, "answer": answer, "channel": channel, "model": model or DEFAULT_MODEL}


def chat_stream(company_id: int, question: str, channel: str = "geo_basic", model: str = None) -> Generator[str, None, None]:
    context = _build_context(company_id, channel)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n上下文信息：\n" + context},
        {"role": "user", "content": question},
    ]

    full_answer = []
    for chunk in _call_llm_stream(messages, model):
        full_answer.append(chunk)
        yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

    answer_text = "".join(full_answer)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO chat_conversations (company_id, channel, question, answer, model, created_at) VALUES (?,?,?,?,?,?)",
            (company_id, channel, question, answer_text, model or DEFAULT_MODEL, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()

    yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
