"""GEO内容合规风险检测 — 蒸馏自2026-07 AI内容监管新规

背景：2026-07-15 AI内容监管新规生效，网信部门集中处置2.6万个违规账号。
四类玩法被判死刑：AI批量垃圾内容铺量、关键词堆砌蹭热词、虚假宣传刷评价、
冒充官方伪造权威背书。AI引擎会对内容做权威信源交叉验证，极限词无佐证直接过滤，
编造数据/引语会反噬品牌可信度评分。

本模块为规则引擎（确定性检测，零LLM成本），检测4类风险：
1. superlative: 极限词（广告法第九条禁用 + AI引擎直接过滤）
2. fake_endorsement: 伪造权威背书（央视上榜/国家推荐/驰名商标/特供专供）
3. absolute_claim: 绝对化承诺（零风险/百分百有效/保证见效）
4. keyword_stuffing: 关键词堆砌（密度超阈值，AI引擎降权）
"""
from __future__ import annotations
import re
from typing import Optional

# 极限词：命中即高风险（广告法第九条 + AI引擎过滤清单）
SUPERLATIVE_TERMS = [
    "最佳", "最好", "最优", "最强", "最先进", "最优秀", "最权威", "最专业",
    "顶级", "顶尖", "极致", "极品", "至尊",
    "首选", "唯一", "独一无二", "绝无仅有", "独家",
    "史无前例", "前无古人", "万能", "永久",
    "全网第一", "全国第一", "全球第一", "行业第一", "销量第一",
    "排名第一", "口碑第一", "服务第一", "质量第一",
    "第一品牌", "第一名", "第一位",
    "世界级", "全球领先", "全国领先",
]

# 需上下文判断的极限词（避免误伤"第一步""第一时间"等正常表述）
_SUPERLATIVE_CONTEXT_PATTERNS = [
    (re.compile(r"(排名|行业|全国|全球|销量|市场|口碑|技术)\s*第一"), "第一（排名类断言）"),
    (re.compile(r"(行业|全国|全球|技术|水平|地位)\s*领先"), "领先（无第三方数据佐证）"),
]

# 需附证书/文件佐证的资质类表述（中风险：真实则补佐证，虚假则红线）
QUALIFICATION_TERMS = [
    ("国家级", "如为真实资质（如国家级高新技术企业），需附证书编号佐证"),
    ("驰名商标", "广告法明确禁止将'驰名商标'用于广告宣传，无论是否真实"),
    ("中国名牌", "'中国名牌'称号已废止，不得用于宣传"),
    ("质量免检", "免检制度已废止，不得宣传'质量免检'"),
]

# 伪造权威背书：命中即高风险（监管四类玩法之一）
FAKE_ENDORSEMENT_TERMS = [
    "央视上榜", "央视推荐", "CCTV推荐", "CCTV上榜", "央视展播",
    "国家推荐", "政府推荐", "国家认证", "国家认可",
    "官方认证", "官方推荐", "官方指定",
    "特供", "专供", "内部专供", "机关专用",
    "专家推荐", "院士推荐", "名医推荐",
    "军队专用", "军用级",
]

# 绝对化承诺：命中即高风险
ABSOLUTE_CLAIM_TERMS = [
    "零风险", "无风险", "百分百有效", "100%有效", "百分之百",
    "保证有效", "保证见效", "保证成功", "无效退款",
    "立竿见影", "药到病除", "根治", "包治", "永不复发",
    "稳赚", "躺赚", "日入过万",
]

# 关键词密度阈值（文章实证：堆砌导致AI可见性-8%，语义模型直接判定垃圾内容）
DENSITY_MEDIUM = 0.05
DENSITY_HIGH = 0.08

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _extract_context(content: str, pos: int, span: int = 20) -> str:
    start = max(0, pos - span)
    end = min(len(content), pos + span)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(content) else ""
    return f"{prefix}{content[start:end]}{suffix}"


def _find_terms(content: str, terms: list, category: str, severity: str, suggestion: str) -> list:
    violations = []
    for term in terms:
        idx = content.find(term)
        while idx != -1:
            violations.append({
                "type": category,
                "severity": severity,
                "term": term,
                "position": idx,
                "context": _extract_context(content, idx),
                "suggestion": suggestion,
            })
            idx = content.find(term, idx + len(term))
    return violations


def _check_superlatives(content: str) -> list:
    violations = _find_terms(
        content, SUPERLATIVE_TERMS, "superlative", "high",
        "删除极限词。AI引擎对无权威佐证的极限词直接过滤，且可能触发平台降权。改用可验证的具体表述（如'服务300+客户'替代'行业第一'）",
    )
    # 已被精确词表命中的区间，上下文模式不再重复标记
    matched_spans = set()
    for v in violations:
        matched_spans.update(range(v["position"], v["position"] + len(v["term"])))

    for pattern, label in _SUPERLATIVE_CONTEXT_PATTERNS:
        for match in pattern.finditer(content):
            if any(pos in matched_spans for pos in range(match.start(), match.end())):
                continue
            violations.append({
                "type": "superlative",
                "severity": "medium",
                "term": label,
                "position": match.start(),
                "context": _extract_context(content, match.start()),
                "suggestion": "补充第三方数据/报告佐证，或改为客观描述",
            })
    return violations


def _check_qualifications(content: str) -> list:
    violations = []
    for term, suggestion in QUALIFICATION_TERMS:
        idx = content.find(term)
        while idx != -1:
            severity = "high" if term in ("驰名商标", "中国名牌", "质量免检") else "medium"
            violations.append({
                "type": "fake_endorsement",
                "severity": severity,
                "term": term,
                "position": idx,
                "context": _extract_context(content, idx),
                "suggestion": suggestion,
            })
            idx = content.find(term, idx + len(term))
    return violations


def _check_fake_endorsements(content: str) -> list:
    return _find_terms(
        content, FAKE_ENDORSEMENT_TERMS, "fake_endorsement", "high",
        "删除伪造背书表述。冒充官方/伪造权威背书属欺诈行为，新规下重罚。权威背书只能靠真实资质、真实媒体报道、真实用户口碑积累",
    )


def _check_absolute_claims(content: str) -> list:
    return _find_terms(
        content, ABSOLUTE_CLAIM_TERMS, "absolute_claim", "high",
        "删除绝对化承诺。AI会对效果声明做权威信源交叉验证，无法验证的声明导致品牌降权",
    )


def _check_keyword_density(content: str, keywords: list) -> list:
    """检测指定关键词的密度。keywords为空时不检测（无法判断内容主题相关性）"""
    violations = []
    total_len = len(content)
    if total_len == 0:
        return violations

    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        count = content.count(kw)
        if count == 0:
            continue
        density = count * len(kw) / total_len
        if density >= DENSITY_HIGH:
            severity, suggestion = "high", (
                f"关键词'{kw}'密度{density:.1%}，远超阈值{DENSITY_HIGH:.0%}。"
                "大模型语义理解可识别堆砌，判定垃圾内容直接降权。删减至自然出现"
            )
        elif density >= DENSITY_MEDIUM:
            severity, suggestion = "medium", (
                f"关键词'{kw}'密度{density:.1%}，超过警戒线{DENSITY_MEDIUM:.0%}。"
                "建议用同义表述和相关内容稀释密度"
            )
        else:
            continue
        violations.append({
            "type": "keyword_stuffing",
            "severity": severity,
            "term": kw,
            "position": content.find(kw),
            "context": f"出现{count}次，密度{density:.1%}",
            "suggestion": suggestion,
        })
    return violations


def check_compliance(content: str, keywords: Optional[list] = None) -> dict:
    """检测内容合规风险

    Args:
        content: 待检测文本
        keywords: 需检测密度的关键词列表（可选，如品牌词/核心产品词）

    Returns:
        risk_level: high/medium/low/pass
        violations: 违规明细（按严重度排序）
        stats: 各类别命中数
    """
    if not content or not content.strip():
        return {"error": "内容为空"}

    violations = []
    violations.extend(_check_superlatives(content))
    violations.extend(_check_qualifications(content))
    violations.extend(_check_fake_endorsements(content))
    violations.extend(_check_absolute_claims(content))
    if keywords:
        violations.extend(_check_keyword_density(content, keywords))

    violations.sort(key=lambda v: (_SEVERITY_ORDER.get(v["severity"], 3), v["position"]))

    high_count = sum(1 for v in violations if v["severity"] == "high")
    medium_count = sum(1 for v in violations if v["severity"] == "medium")

    if high_count > 0:
        risk_level = "high"
    elif medium_count > 0:
        risk_level = "medium"
    elif violations:
        risk_level = "low"
    else:
        risk_level = "pass"

    stats = {}
    for v in violations:
        stats[v["type"]] = stats.get(v["type"], 0) + 1

    return {
        "risk_level": risk_level,
        "total_violations": len(violations),
        "high_count": high_count,
        "medium_count": medium_count,
        "stats": stats,
        "violations": violations,
        "content_length": len(content),
    }


def get_rules() -> list:
    """返回检测规则说明（供前端展示/API文档）"""
    return [
        {
            "key": "superlative",
            "name": "极限词检测",
            "description": "广告法第九条禁用词 + AI引擎直接过滤的无佐证极限表述",
            "basis": "2026-07 AI内容监管新规：无权威信源佐证的极限词直接过滤",
        },
        {
            "key": "fake_endorsement",
            "name": "伪造权威背书检测",
            "description": "冒充官方、伪造专家/媒体/国家背书、已废止称号",
            "basis": "新规四类红线玩法之一：欺诈性质，抓到重罚",
        },
        {
            "key": "absolute_claim",
            "name": "绝对化承诺检测",
            "description": "零风险/保证有效等无法验证的效果声明",
            "basis": "AI对效果声明做权威信源交叉验证，圆不上会反噬可信度",
        },
        {
            "key": "keyword_stuffing",
            "name": "关键词堆砌检测",
            "description": f"关键词密度超过{DENSITY_MEDIUM:.0%}警戒线/{DENSITY_HIGH:.0%}红线",
            "basis": "实证数据：关键词堆砌导致AI引擎可见性-8%",
        },
    ]
