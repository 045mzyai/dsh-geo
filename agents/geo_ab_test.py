"""GEO A/B测试Agent — 蒸馏自郝攀《官网GEO项目实战复盘》

核心方法论：
1. 固定问题集×固定AI平台×优化前后对比
2. 信源分类统计（官网/B2B/自媒体/其他），不混在一起算
3. 不新增内容，仅做SEO+GEO适配改造，验证改造本身的效果
4. 监测4类页面被AI引用的情况（产品详情/行业方案/首页/PDF）

实测数据：84问题×6平台，AI引用提升2-3倍
"""
from __future__ import annotations
import json
import logging
import sqlite3
from datetime import datetime
from typing import Optional
import requests
from config import MZY_API_KEY, MZY_BASE_URL, DEFAULT_MODEL, DB_PATH

logger = logging.getLogger(__name__)

DEFAULT_PLATFORMS = ["kimi-k3", "deepseek-v4-pro", "glm-5.2", "minimax-m3", "hy3"]

PAGE_TYPES = [
    {"key": "product_detail", "name": "产品详情页", "description": "回答设备是什么、具备什么能力、适合哪些需求"},
    {"key": "industry_solution", "name": "行业应用方案页", "description": "帮助AI理解产品可以进入哪些行业、解决哪些具体问题"},
    {"key": "homepage", "name": "网站主页", "description": "用于确认企业身份和综合业务"},
    {"key": "product_pdf", "name": "产品单页PDF", "description": "承载更完整的规格、参数、型号和技术资料"},
]

SOURCE_CATEGORIES = [
    {"key": "official_site", "name": "官网", "description": "企业自有域名下的页面"},
    {"key": "b2b_platform", "name": "B2B平台", "description": "如1688、阿里巴巴等"},
    {"key": "self_media", "name": "官方自媒体", "description": "百家号、公众号、短视频账号等"},
    {"key": "third_party_media", "name": "第三方媒体", "description": "新闻源站点报道"},
    {"key": "other", "name": "其他", "description": "无法分类的信源"},
]


def _call_llm(question: str, model: str = None) -> str:
    model = model or DEFAULT_MODEL
    resp = requests.post(
        f"{MZY_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {MZY_API_KEY}"},
        json={"model": model, "messages": [{"role": "user", "content": question}], "temperature": 0.5},
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _detect_brand_mention(response: str, company_name: str, brand_aliases: list = None) -> dict:
    """检测AI回答中是否提及品牌"""
    names = [company_name]
    if brand_aliases:
        names.extend(brand_aliases)
    found = []
    for name in names:
        if name and name in response:
            found.append(name)
    return {
        "mentioned": len(found) > 0,
        "matched_names": list(set(found)),
        "response_length": len(response),
    }


def _classify_source(response: str, company_domain: str = "") -> str:
    """分类AI回答中的信源（简化版：基于关键词匹配）"""
    lower = response.lower()
    if company_domain and company_domain.lower() in lower:
        return "official_site"
    b2b_markers = ["1688", "alibaba", "made-in-china", "hc360", "b2b"]
    for m in b2b_markers:
        if m in lower:
            return "b2b_platform"
    media_markers = ["baijiahao", "公众号", "抖音", "快手", "视频号"]
    for m in media_markers:
        if m in lower:
            return "self_media"
    news_markers = ["新闻", "报道", "讯网", "新浪网", "网易", "腾讯网"]
    for m in news_markers:
        if m in lower:
            return "third_party_media"
    return "other"


def create_test_suite(company_id: int, name: str, questions: list, platforms: list = None) -> dict:
    """创建GEO A/B测试套件"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute(
            "INSERT INTO geo_ab_tests (company_id, name, questions_json, platforms_json, status, created_at) VALUES (?,?,?,?,?,?)",
            (company_id, name, json.dumps(questions, ensure_ascii=False), json.dumps(platforms or DEFAULT_PLATFORMS), "created", datetime.now().isoformat()),
        )
        test_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()
    return {"id": test_id, "name": name, "questions": questions, "platforms": platforms or DEFAULT_PLATFORMS, "status": "created"}


def run_test_batch(test_id: int, company_name: str, company_domain: str = "", brand_aliases: list = None, phase: str = "before") -> dict:
    """执行一轮测试（before或after）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        test = conn.execute("SELECT * FROM geo_ab_tests WHERE id=?", (test_id,)).fetchone()
        if not test:
            return {"error": "测试套件不存在"}
        questions = json.loads(test["questions_json"])
        platforms = json.loads(test["platforms_json"])
    finally:
        conn.close()

    results = []
    for platform in platforms:
        for question in questions:
            try:
                response = _call_llm(question, platform)
                mention = _detect_brand_mention(response, company_name, brand_aliases)
                source = _classify_source(response, company_domain) if mention["mentioned"] else "none"
                results.append({
                    "platform": platform,
                    "question": question,
                    "response": response,
                    "mentioned": mention["mentioned"],
                    "matched_names": mention["matched_names"],
                    "source": source,
                    "response_length": mention["response_length"],
                })
            except Exception as e:
                logger.warning("测试失败 %s/%s: %s", platform, question[:20], e)
                results.append({
                    "platform": platform,
                    "question": question,
                    "error": str(e),
                    "mentioned": False,
                    "source": "error",
                })

    stats = _compute_stats(results, platforms)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE geo_ab_tests SET results_json=?, status=?, completed_at=? WHERE id=?",
            (json.dumps({"phase": phase, "results": results, "stats": stats}, ensure_ascii=False), f"{phase}_completed", datetime.now().isoformat(), test_id),
        )
        conn.commit()
    finally:
        conn.close()

    return {"test_id": test_id, "phase": phase, "results": results, "stats": stats}


def _compute_stats(results: list, platforms: list) -> dict:
    by_platform = {}
    by_source = {cat["key"]: 0 for cat in SOURCE_CATEGORIES}
    by_source["none"] = 0
    total_mentions = 0
    total_queries = len(results)

    for r in results:
        platform = r["platform"]
        if platform not in by_platform:
            by_platform[platform] = {"total": 0, "mentioned": 0, "official_site": 0}
        by_platform[platform]["total"] += 1
        if r.get("mentioned"):
            by_platform[platform]["mentioned"] += 1
            total_mentions += 1
            source = r.get("source", "other")
            by_platform[platform][source] = by_platform[platform].get(source, 0) + 1
            if source in by_source:
                by_source[source] += 1
            else:
                by_source["other"] += 1
        else:
            by_source["none"] += 1

    for platform in by_platform:
        data = by_platform[platform]
        data["mention_rate"] = round(data["mentioned"] / data["total"] * 100, 1) if data["total"] > 0 else 0
        data["official_rate"] = round(data.get("official_site", 0) / data["total"] * 100, 1) if data["total"] > 0 else 0

    return {
        "total_queries": total_queries,
        "total_mentions": total_mentions,
        "overall_mention_rate": round(total_mentions / total_queries * 100, 1) if total_queries > 0 else 0,
        "by_platform": by_platform,
        "by_source": by_source,
        "official_site_mentions": by_source.get("official_site", 0),
        "official_site_rate": round(by_source.get("official_site", 0) / total_queries * 100, 1) if total_queries > 0 else 0,
    }


def compare_phases(test_id: int) -> dict:
    """对比优化前后数据"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        test = conn.execute("SELECT * FROM geo_ab_tests WHERE id=?", (test_id,)).fetchone()
        if not test:
            return {"error": "测试套件不存在"}
        results_json = test["results_json"]
        if not results_json:
            return {"error": "尚无测试结果"}
        data = json.loads(results_json)
        stats = data.get("stats", {})
        return {"test_id": test_id, "name": test["name"], "phase": data.get("phase"), "stats": stats}
    finally:
        conn.close()


def get_test_suites(company_id: int = None) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if company_id:
            rows = conn.execute("SELECT * FROM geo_ab_tests WHERE company_id=? ORDER BY created_at DESC", (company_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM geo_ab_tests ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_page_types() -> list:
    return PAGE_TYPES


def get_source_categories() -> list:
    return SOURCE_CATEGORIES
