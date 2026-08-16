"""六层成熟度评分Agent — 蒸馏自郝攀六层全域AI营销增长模型

SEO→AEO→GEO→GAO→GMO→GDO 六层评分，定位企业AI营销成熟度

| 层级 | 名称 | 目标 | 对应能力 |
|------|------|------|---------|
| L1 | SEO基础检索层 | 搜得到 | 网站可抓取收录 |
| L2 | AEO语义解析层 | 读得懂 | 结构化语义内容 |
| L3 | GEO算法推荐层 | 推得出 | AI引用品牌 |
| L4 | GAO心智沉淀层 | 记得住 | 品牌信息统一 |
| L5 | GMO商业触达层 | 找上门 | 联系方式可查 |
| L6 | GDO决策背书层 | 签得了 | 决策证据可验证 |
"""
from __future__ import annotations
import json
import logging
from typing import Optional
import requests
from config import MZY_API_KEY, MZY_BASE_URL, DEFAULT_MODEL

logger = logging.getLogger(__name__)

LAYERS = [
    {
        "key": "seo",
        "name": "SEO基础检索层",
        "goal": "搜得到",
        "description": "企业官网、产品、服务、案例与品牌信息能够被搜索引擎正常抓取和收录",
        "weight": 15,
        "scoring_criteria": {
            "has_sitemap": "存在sitemap.xml",
            "has_robots_txt": "存在robots.txt",
            "https_enabled": "启用HTTPS",
            "meta_complete": "Title和Description标签完整",
            "page_indexable": "页面可被搜索引擎索引",
        },
    },
    {
        "key": "aeo",
        "name": "AEO语义解析层",
        "goal": "读得懂",
        "description": "通过结构化、问答化和语义清晰的内容，让大模型准确理解企业是谁、提供什么服务",
        "weight": 15,
        "scoring_criteria": {
            "has_json_ld": "存在JSON-LD结构化数据",
            "has_llms_txt": "存在llms.txt文件",
            "semantic_html": "语义化HTML标签（H1/H2层次清晰）",
            "qa_content": "有FAQ或问答格式内容",
            "content_depth": "页面文本内容充足（≥500字）",
        },
    },
    {
        "key": "geo",
        "name": "GEO算法推荐层",
        "goal": "推得出",
        "description": "品牌在行业推荐、产品选型、服务商筛选中进入大模型答案",
        "weight": 20,
        "scoring_criteria": {
            "ai_citation_rate": "AI引用率（基准测试）",
            "keyword_coverage": "关键词覆盖面（拓词维度数）",
            "content_strategies": "内容优化策略应用数",
            "sheep_score": "SHEEP评分",
            "benchmark_rank": "基准测试排名",
        },
    },
    {
        "key": "gao",
        "name": "GAO心智沉淀层",
        "goal": "记得住",
        "description": "统一企业在官网、媒体、自媒体和其他信源中的品牌信息，减少内容冲突",
        "weight": 15,
        "scoring_criteria": {
            "brand_consistency": "品牌信息跨平台一致性",
            "advantage_tags": "优势标签明确且统一",
            "industry_positioning": "行业定位清晰",
            "content_frequency": "内容更新频率",
        },
    },
    {
        "key": "gmo",
        "name": "GMO商业触达层",
        "goal": "找上门",
        "description": "完善企业官网入口、品牌主体、联系方式和咨询通道",
        "weight": 15,
        "scoring_criteria": {
            "has_contact_page": "存在联系页面",
            "has_phone": "有联系电话",
            "has_email": "有邮箱",
            "has_address": "有地址",
            "has_consult_channel": "有咨询入口（表单/在线客服）",
        },
    },
    {
        "key": "gdo",
        "name": "GDO决策背书层",
        "goal": "签得了",
        "description": "围绕真实案例、客户反馈、团队能力、资质证明建立可验证的决策证据",
        "weight": 20,
        "scoring_criteria": {
            "case_detail": "案例详情完整度",
            "service_process": "服务流程透明度",
            "differentiation": "差异化定位清晰度",
            "third_party": "第三方信源覆盖度",
            "evidence_chain": "证据链一致性",
        },
    },
]


def _score_from_diagnosis(diagnosis: dict) -> dict:
    """从网站诊断数据提取各层得分"""
    scores = {}
    checks = diagnosis.get("checks", {}) if diagnosis else {}

    # L1: SEO
    seo_score = 0
    if diagnosis.get("score", 0) > 0:
        seo_score = min(100, diagnosis.get("score", 0))
    scores["seo"] = {"score": seo_score, "details": {"诊断评分": diagnosis.get("score", 0)}}

    # L2: AEO
    aeo_score = 0
    sd = checks.get("structured_data", {})
    if sd.get("json_ld_count", 0) > 0:
        aeo_score += 25
    llms = checks.get("llms_txt", {})
    if llms.get("exists"):
        aeo_score += 25
    ai_read = checks.get("ai_readability", {})
    if ai_read.get("h1_count", 0) > 0:
        aeo_score += 15
    if ai_read.get("h2_count", 0) > 0:
        aeo_score += 15
    if ai_read.get("text_length", 0) > 500:
        aeo_score += 20
    scores["aeo"] = {"score": aeo_score, "details": {"JSON-LD": sd.get("json_ld_count", 0), "llms.txt": llms.get("exists", False), "文本长度": ai_read.get("text_length", 0)}}

    # L4: GMO
    gmo_score = 0
    links = checks.get("links", {})
    contact = checks.get("contact_info", {})
    if contact.get("has_phone") or links.get("external_count", 0) > 0:
        gmo_score += 25
    if contact.get("has_email"):
        gmo_score += 25
    if contact.get("has_address"):
        gmo_score += 25
    if contact.get("has_contact_page"):
        gmo_score += 25
    scores["gmo"] = {"score": gmo_score, "details": contact}

    return scores


def _score_from_benchmark(benchmark: dict) -> dict:
    """从基准测试数据提取GEO层得分"""
    citation_rate = benchmark.get("citation_rate", 0)
    avg_rank = benchmark.get("avg_rank", 0)

    geo_score = 0
    if citation_rate > 0:
        geo_score = min(100, int(citation_rate * 100))
    if avg_rank > 0 and avg_rank <= 3:
        geo_score += 10
    geo_score = min(100, geo_score)

    return {"geo": {"score": geo_score, "details": {"引用率": f"{citation_rate*100:.1f}%", "平均排名": avg_rank}}}


def _score_from_sheep(sheep: dict) -> dict:
    """从SHEEP评分提取GEO层补充得分"""
    gem_score = sheep.get("gem_score", 0)
    return {"geo_supplement": {"score": gem_score, "details": sheep.get("level", "")}}


def _score_from_gdo(gdo: dict) -> dict:
    """从GDO审计提取L6得分"""
    score = gdo.get("overall_score", 0)
    return {"gdo": {"score": score, "details": {"level": gdo.get("level", "D"), "summary": gdo.get("summary", "")[:100]}}}


def calculate_maturity(diagnosis: dict = None, benchmark: dict = None, sheep: dict = None, gdo: dict = None, keywords_count: int = 0, strategies_count: int = 0) -> dict:
    """计算六层成熟度评分"""

    layer_scores = {}

    # 从各数据源提取
    if diagnosis:
        diag_scores = _score_from_diagnosis(diagnosis)
        layer_scores.update(diag_scores)

    if benchmark:
        bench_scores = _score_from_benchmark(benchmark)
        layer_scores.update(bench_scores)

    if sheep:
        sheep_scores = _score_from_sheep(sheep)
        if "geo" in layer_scores and "geo_supplement" in sheep_scores:
            current = layer_scores["geo"]["score"]
            supplement = sheep_scores["geo_supplement"]["score"]
            layer_scores["geo"]["score"] = min(100, (current + supplement) // 2)

    if gdo:
        gdo_scores = _score_from_gdo(gdo)
        layer_scores.update(gdo_scores)

    # 补充GEO层（关键词+策略）
    geo_extra = 0
    if keywords_count > 0:
        geo_extra += min(20, keywords_count)
    if strategies_count > 0:
        geo_extra += min(10, strategies_count)
    if "geo" in layer_scores:
        layer_scores["geo"]["score"] = min(100, layer_scores["geo"]["score"] + geo_extra)
    elif geo_extra > 0:
        layer_scores["geo"] = {"score": min(100, geo_extra * 2), "details": {"关键词数": keywords_count, "策略数": strategies_count}}

    # GAO层：默认从诊断中推断
    if "gao" not in layer_scores:
        gao_score = 0
        if diagnosis:
            checks = diagnosis.get("checks", {})
            meta = checks.get("meta_tags", {})
            if meta.get("title"):
                gao_score += 30
            if meta.get("description"):
                gao_score += 30
            sd = checks.get("structured_data", {})
            if sd.get("json_ld_count", 0) > 0:
                gao_score += 20
            if checks.get("ai_readability", {}).get("text_length", 0) > 1000:
                gao_score += 20
        layer_scores["gao"] = {"score": gao_score, "details": {"品牌信息一致性": "基于meta标签和结构化数据推断"}}

    # 填充未评估的层
    for layer in LAYERS:
        if layer["key"] not in layer_scores:
            layer_scores[layer["key"]] = {"score": 0, "details": {"状态": "未评估"}}

    # 计算加权总分
    total_weight = sum(l["weight"] for l in LAYERS)
    weighted_sum = sum(layer_scores[l["key"]]["score"] * l["weight"] for l in LAYERS)
    overall_score = round(weighted_sum / total_weight) if total_weight > 0 else 0

    # 确定成熟度等级
    if overall_score >= 85:
        level = "S"
        level_label = "卓越"
    elif overall_score >= 70:
        level = "A"
        level_label = "优秀"
    elif overall_score >= 55:
        level = "B"
        level_label = "良好"
    elif overall_score >= 40:
        level = "C"
        level_label = "基础"
    else:
        level = "D"
        level_label = "起步"

    # 识别最薄弱的层
    weakest = min(LAYERS, key=lambda l: layer_scores[l["key"]]["score"])
    strongest = max(LAYERS, key=lambda l: layer_scores[l["key"]]["score"])

    layers_result = []
    for layer in LAYERS:
        score_data = layer_scores[layer["key"]]
        layers_result.append({
            "key": layer["key"],
            "name": layer["name"],
            "goal": layer["goal"],
            "description": layer["description"],
            "weight": layer["weight"],
            "score": score_data["score"],
            "level": "S" if score_data["score"] >= 90 else "A" if score_data["score"] >= 80 else "B" if score_data["score"] >= 70 else "C" if score_data["score"] >= 60 else "D",
            "details": score_data.get("details", {}),
            "scoring_criteria": layer["scoring_criteria"],
        })

    return {
        "layers": layers_result,
        "overall_score": overall_score,
        "level": level,
        "level_label": level_label,
        "weakest_layer": {"key": weakest["key"], "name": weakest["name"], "goal": weakest["goal"], "score": layer_scores[weakest["key"]]["score"]},
        "strongest_layer": {"key": strongest["key"], "name": strongest["name"], "goal": strongest["goal"], "score": layer_scores[strongest["key"]]["score"]},
        "model": "六层全域AI营销增长模型（SEO→AEO→GEO→GAO→GMO→GDO）",
        "source": "郝攀《从推荐到成交》",
    }


def get_layers() -> list:
    return [{"key": l["key"], "name": l["name"], "goal": l["goal"], "description": l["description"], "weight": l["weight"], "scoring_criteria": l["scoring_criteria"]} for l in LAYERS]
