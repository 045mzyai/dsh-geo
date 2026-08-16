"""SHEEP GEM评分Agent — 蒸馏自CN-Sheep/SheepGeo框架

五维评估模型:
  S (Semantic Coverage, 25%): AI模型识别率+内容质量+跨模型覆盖
  H (Human Credibility, 25%): 领域权威+作者专业度+来源可验证性+社会证明
  E1 (Evidence Structuring, 20%): Schema.org结构化数据+信息架构+认知负荷
  E2 (Ecosystem Integration, 15%): 多平台可见性+交叉引用网络+API可访问性
  P (Performance Monitoring, 15%): AI采纳率+转化潜力+用户留存+技术性能

GEM Score = S×0.25 + H×0.25 + E1×0.20 + E2×0.15 + P×0.15

9个中国AI模型权重:
  Qwen 15%, Doubao 14%, ERNIE 13%, GLM-4 12%, Moonshot 11%,
  DeepSeek 10%, Spark 9%, Hunyuan 8%, Mita 8%
"""

import json
import logging
import requests
from config import MZY_API_KEY, MZY_BASE_URL, DEFAULT_MODEL

logger = logging.getLogger(__name__)

MODEL_TEMPS = {"kimi-k3": 1.0}

# 自一致性采样数：质量优先，多次采样取中位数压制S/H等主观维度评分噪声
SHEEP_SAMPLE_COUNT = 3

# 9个中国AI模型权重 (蒸馏自SheepGeo)
CN_AI_MODEL_WEIGHTS = {
    "qwen": 0.15,
    "doubao": 0.14,
    "ernie": 0.13,
    "glm-4": 0.12,
    "moonshot": 0.11,
    "deepseek": 0.10,
    "spark": 0.09,
    "hunyuan": 0.08,
    "mita": 0.08,
}

# 评分等级 (蒸馏自SheepGeo)
GRADE_THRESHOLDS = [
    (90, "A+"),
    (80, "A"),
    (70, "B+"),
    (60, "B"),
    (50, "C+"),
    (40, "C"),
    (0, "D"),
]


def _grade(score: float) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "D"


# ── 五维评估prompt ──

SHEEP_EVAL_PROMPT = """你是一个GEO（生成式引擎优化）评估专家，使用SHEEP五维模型评估目标公司在AI搜索引擎中的综合表现。

目标公司：{company_name}
行业：{industry}
网站URL：{url}

请从以下5个维度评分（0-100分）：

## S维度 - 语义覆盖度 (Semantic Coverage)
评估AI模型对公司内容的识别和理解程度：
- AI模型识别率：在主流AI搜索引擎中搜索公司相关词时，是否被提及
- 内容质量：内容是否详实、准确、结构化
- 跨模型覆盖：在多个AI模型中是否都有覆盖
评分依据：{s_evidence}

## H维度 - 人类可信度 (Human Credibility)
评估公司的权威性和可信度信号：
- 领域权威：公司在行业中的地位和知名度
- 作者专业度：内容作者的专业背景和资质
- 来源可验证性：信息是否有可验证的来源和引用
- 社会证明：是否有用户评价、案例、媒体报道
评分依据：{h_evidence}

## E1维度 - 证据结构化 (Evidence Structuring)
评估内容对AI理解友好的结构化程度：
- Schema.org结构化数据：是否使用结构化标记
- 信息架构：内容组织是否清晰（标题/段落/列表）
- 认知负荷：信息是否易于AI解析和理解
评分依据：{e1_evidence}

## E2维度 - 生态集成度 (Ecosystem Integration)
评估在多平台的可见性和互联程度：
- 多平台可见性：在多少个平台有官方 presence
- 交叉引用网络：是否被其他权威来源引用
- API可访问性：内容是否可通过API或结构化方式获取
评分依据：{e2_evidence}

## P维度 - 性能监控 (Performance Monitoring)
评估从AI推荐到用户转化的效果：
- AI采纳率：AI推荐后用户实际访问的比例
- 转化潜力：AI推荐内容是否能转化为实际业务
- 用户留存：用户通过AI推荐访问后的留存情况
- 技术性能：网站加载速度、可访问性
评分依据：{p_evidence}

返回JSON：
{{
  "S": 0-100,
  "H": 0-100,
  "E1": 0-100,
  "E2": 0-100,
  "P": 0-100,
  "S_details": "该维度的具体分析",
  "H_details": "该维度的具体分析",
  "E1_details": "该维度的具体分析",
  "E2_details": "该维度的具体分析",
  "P_details": "该维度的具体分析",
  "improvement_suggestions": ["改进建议1", "改进建议2", "改进建议3"]
}}"""


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
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def calculate_gem_score(company_name: str, industry: str = "", url: str = "",
                        evidence: dict = None, diagnosis: dict = None) -> dict:
    """计算SHEEP GEM评分（自一致性多采样 + 证据锚定反思）

    质量优先原则，两层LLM能力提升机制：
    1. 自一致性多采样：SHEEP_SAMPLE_COUNT次采样取每维度中位数，压制主观维度评分噪声
    2. 证据锚定反思：用客观诊断证据校验评分一致性，发现"证据强但评分低"的矛盾时触发反思重评

    Args:
        evidence: 各维度的证据材料，如 {"s_evidence": "在deepseek中搜索被提及", ...}
        diagnosis: 原始诊断数据（可选），用于反思阶段的证据锚定校验
    """
    if evidence is None:
        evidence = {}

    prompt = SHEEP_EVAL_PROMPT.format(
        company_name=company_name,
        industry=industry or "科技",
        url=url or "未提供",
        s_evidence=evidence.get("s_evidence", "请根据已知信息评估"),
        h_evidence=evidence.get("h_evidence", "请根据已知信息评估"),
        e1_evidence=evidence.get("e1_evidence", "请根据已知信息评估"),
        e2_evidence=evidence.get("e2_evidence", "请根据已知信息评估"),
        p_evidence=evidence.get("p_evidence", "请根据已知信息评估"),
    )

    # 自一致性多采样：每维度取中位数，压制S/H等主观维度的评分噪声
    samples = []
    for i in range(SHEEP_SAMPLE_COUNT):
        try:
            raw = _call_llm(prompt, temperature=0.5, json_mode=True)
            samples.append(json.loads(raw))
        except Exception as e:
            logger.warning("SHEEP采样%d失败: %s", i + 1, e)

    if samples:
        result = _consensus_result(samples)
    else:
        logger.error("SHEEP全部采样失败")
        result = {"S": 0, "H": 0, "E1": 0, "E2": 0, "P": 0,
                  "S_details": "评估失败", "H_details": "", "E1_details": "", "E2_details": "", "P_details": "",
                  "improvement_suggestions": []}

    # 反思机制：证据锚定一致性校验（仅在有诊断数据时启用）
    reflection = {"triggered": False, "contradictions": [], "adjustments": {}}
    if diagnosis:
        contradictions = _reflect_check(result, diagnosis)
        if contradictions:
            reflection["triggered"] = True
            reflection["contradictions"] = contradictions
            before = {k: result.get(k, 0) for k in ("S", "H", "E1", "E2", "P")}

            reflect_prompt = prompt + (
                "\n\n【评分反思】你上一次的评分与以下客观证据存在矛盾，请严格基于证据重新评估，不要凭空给分：\n"
                + "\n".join(f"- {c}" for c in contradictions)
                + "\n请重新输出修正后的JSON（格式同上）。只输出JSON。"
            )
            try:
                raw2 = _call_llm(reflect_prompt, temperature=0.2, json_mode=True)
                result2 = json.loads(raw2)
                if any(result2.get(k, 0) != before.get(k, 0) for k in before):
                    reflection["adjustments"] = {
                        k: {"before": before.get(k, 0), "after": result2.get(k, 0)}
                        for k in before
                    }
                    result = result2
            except Exception as e:
                logger.warning("SHEEP反思重评失败，保留初评: %s", e)

    # 计算GEM加权总分
    s = result.get("S", 0)
    h = result.get("H", 0)
    e1 = result.get("E1", 0)
    e2 = result.get("E2", 0)
    p = result.get("P", 0)

    gem_score = round(s * 0.25 + h * 0.25 + e1 * 0.20 + e2 * 0.15 + p * 0.15, 1)
    grade = _grade(gem_score)

    # 各维度等级
    dim_grades = {
        "S": {"score": s, "grade": _grade(s), "weight": "25%", "name": "语义覆盖度"},
        "H": {"score": h, "grade": _grade(h), "weight": "25%", "name": "人类可信度"},
        "E1": {"score": e1, "grade": _grade(e1), "weight": "20%", "name": "证据结构化"},
        "E2": {"score": e2, "grade": _grade(e2), "weight": "15%", "name": "生态集成度"},
        "P": {"score": p, "grade": _grade(p), "weight": "15%", "name": "性能监控"},
    }

    return {
        "company_name": company_name,
        "gem_score": gem_score,
        "grade": grade,
        "dimensions": dim_grades,
        "details": {
            "S": result.get("S_details", ""),
            "H": result.get("H_details", ""),
            "E1": result.get("E1_details", ""),
            "E2": result.get("E2_details", ""),
            "P": result.get("P_details", ""),
        },
        "improvement_suggestions": result.get("improvement_suggestions", []),
        "model_weights": CN_AI_MODEL_WEIGHTS,
        "reflection": reflection,
    }


def _consensus_result(samples: list) -> dict:
    """多采样共识：每维度取中位数作为最终分数。

    details与建议取自GEM最接近共识总分的样本，保证文字说明与分数自洽。
    """
    dims = ("S", "H", "E1", "E2", "P")
    weights = {"S": 0.25, "H": 0.25, "E1": 0.20, "E2": 0.15, "P": 0.15}

    def median(vals):
        vals = sorted(vals)
        n = len(vals)
        mid = n // 2
        return vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2

    consensus = {k: median([s.get(k, 0) for s in samples]) for k in dims}
    consensus_gem = sum(consensus[k] * weights[k] for k in dims)

    def sample_gem(s):
        return sum(s.get(k, 0) * weights[k] for k in dims)

    best = min(samples, key=lambda s: abs(sample_gem(s) - consensus_gem))
    merged = dict(best)
    merged.update(consensus)
    return merged


def _reflect_check(result: dict, diagnosis: dict) -> list:
    """证据锚定反思校验：用客观诊断信号检测评分与证据的矛盾。

    规则为"证据下限"——证据明确存在某能力，但LLM评分明显偏低（低于下限10分以上），
    判定为评分与证据脱节，返回矛盾描述供反思重评。宽松下限避免扭曲LLM判断。

    PageDiagnoser checks结构: https/meta_tags/structured_data/llms_txt/headings/links/ai_readability
    """
    contradictions = []
    checks = diagnosis.get("checks", {})

    # E2锚定：llms.txt已部署 → 生态集成有实质动作
    llms = checks.get("llms_txt", {})
    if llms.get("llms_txt"):
        floor = 60
        if result.get("E2", 0) < floor - 10:
            contradictions.append(
                f"E2生态集成度：证据显示llms.txt已部署，这是明确的AI生态集成动作，评分{result.get('E2', 0)}偏低（证据下限{floor}）"
            )

    # E1锚定：JSON-LD结构化数据>=2个 → 证据结构化有实质建设
    sd = checks.get("structured_data", {})
    if sd.get("json_ld_count", 0) >= 2:
        floor = 65
        if result.get("E1", 0) < floor - 10:
            contradictions.append(
                f"E1证据结构化：证据显示已有{sd.get('json_ld_count')}个JSON-LD结构化数据，评分{result.get('E1', 0)}偏低（证据下限{floor}）"
            )

    # P锚定：诊断分>=90且HTTP 200 → 传播性能良好
    overall = diagnosis.get("score", 0)
    status = diagnosis.get("status_code", 0)
    if overall >= 90 and status == 200:
        floor = 70
        if result.get("P", 0) < floor - 10:
            contradictions.append(
                f"P性能监控：证据显示页面诊断分{overall}/100且HTTP {status}，评分{result.get('P', 0)}偏低（证据下限{floor}）"
            )

    # S锚定：中文字符>=1000 → 语义内容有实质规模
    ar = checks.get("ai_readability", {})
    if ar.get("chinese_chars", 0) >= 1000:
        floor = 55
        if result.get("S", 0) < floor - 10:
            contradictions.append(
                f"S语义覆盖度：证据显示页面含{ar.get('chinese_chars')}个中文字符，语义内容有实质规模，评分{result.get('S', 0)}偏低（证据下限{floor}）"
            )

    # H锚定：HTTPS+联系方式+地址齐全 → 可信度基础扎实
    https_ok = checks.get("https", {}).get("pass", False)
    has_contact = ar.get("has_contact_info", False)
    has_address = ar.get("has_address", False)
    if https_ok and has_contact and has_address:
        floor = 60
        if result.get("H", 0) < floor - 10:
            contradictions.append(
                f"H人类可信度：证据显示HTTPS有效且联系方式/地址齐全，评分{result.get('H', 0)}偏低（证据下限{floor}）"
            )

    return contradictions


def get_model_weights() -> dict:
    """获取9个中国AI模型权重"""
    return CN_AI_MODEL_WEIGHTS


def build_evidence_from_diagnosis(diag: dict) -> dict:
    """从PageDiagnoser诊断结果构建SHEEP五维证据材料

    PageDiagnoser返回结构:
      checks.https: {pass, detail}
      checks.meta_tags: {title, has_description, description, has_viewport, pass}
      checks.structured_data: {json_ld_count, schema_types, microdata_count, pass}
      checks.llms_txt: {llms_txt, ai_txt, pass}
      checks.headings: {h1_count, h2_count, h3_count, pass}
      checks.links: {total, internal, external, pass}
      checks.ai_readability: {text_length, chinese_chars, word_count, has_contact_info, has_address, pass}
      score, status_code, html_size
    """
    checks = diag.get("checks", {})
    url = diag.get("url", "")
    score = diag.get("score", 0)
    status_code = diag.get("status_code", 0)
    html_size = diag.get("html_size", 0)

    # S维度证据 ← meta_tags + ai_readability
    meta = checks.get("meta_tags", {})
    ai_read = checks.get("ai_readability", {})
    title = meta.get("title", "") or ""
    desc = meta.get("description", "") or ""
    text_len = ai_read.get("text_length", 0)
    chinese_chars = ai_read.get("chinese_chars", 0)
    s_evidence = (
        f"页面标题'{title}'（{len(title)}字），"
        f"meta描述{len(desc)}字，"
        f"正文{text_len}字，中文字符{chinese_chars}个。"
        f"{'内容充实，AI可提取信息多' if chinese_chars > 200 else '内容偏少，AI可提取信息有限'}。"
    )

    # H维度证据 ← https + ai_readability(联系方式/地址)
    https = checks.get("https", {})
    https_ok = https.get("pass", False)
    has_contact = ai_read.get("has_contact_info", False)
    has_address = ai_read.get("has_address", False)
    h_signals = []
    if https_ok:
        h_signals.append("HTTPS有效")
    if has_contact:
        h_signals.append("有联系方式")
    if has_address:
        h_signals.append("有地址信息")
    h_evidence = (
        f"HTTPS: {'有效' if https_ok else '无效'}。"
        f"信任信号: {'、'.join(h_signals) if h_signals else '未找到'}。"
        f"{'可信度信号充足' if len(h_signals) >= 3 else '可信度信号不足，建议补充联系方式和公司信息'}。"
    )

    # E1维度证据 ← structured_data + headings
    sd = checks.get("structured_data", {})
    json_ld_count = sd.get("json_ld_count", 0)
    schema_types = sd.get("schema_types", [])
    headings = checks.get("headings", {})
    h1_count = headings.get("h1_count", 0)
    h2_count = headings.get("h2_count", 0)
    h3_count = headings.get("h3_count", 0)
    e1_evidence = (
        f"JSON-LD结构化数据: {json_ld_count}个"
        f"（类型: {', '.join(schema_types) if schema_types else '无'}）。"
        f"标题层级: H1×{h1_count} H2×{h2_count} H3×{h3_count}。"
        f"{'结构化良好，AI易解析' if json_ld_count > 0 and h1_count > 0 else '缺少结构化数据，建议添加JSON-LD和清晰标题层级'}。"
    )

    # E2维度证据 ← links + llms_txt
    links = checks.get("links", {})
    internal = links.get("internal", 0)
    external = links.get("external", 0)
    llms = checks.get("llms_txt", {})
    has_llms = llms.get("llms_txt", False)
    has_robots = llms.get("ai_txt", False)
    e2_evidence = (
        f"内链{internal}个，外链{external}个。"
        f"llms.txt: {'存在' if has_llms else '缺失'}。"
        f"ai.txt: {'存在' if has_robots else '缺失'}。"
        f"{'生态集成良好' if has_llms and external > 0 else '建议添加llms.txt和更多外链引用'}。"
    )

    # P维度证据 ← status_code + html_size + score
    p_evidence = (
        f"HTTP状态: {status_code}。"
        f"页面大小: {html_size // 1024}KB。"
        f"诊断评分: {score}/100。"
        f"{'技术性能良好' if status_code == 200 and score >= 60 else '技术性能需优化'}。"
    )

    return {
        "s_evidence": s_evidence,
        "h_evidence": h_evidence,
        "e1_evidence": e1_evidence,
        "e2_evidence": e2_evidence,
        "p_evidence": p_evidence,
    }
