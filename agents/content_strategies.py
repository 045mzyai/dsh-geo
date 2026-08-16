"""GEO内容优化策略Agent — 蒸馏自GEO-optim/GEO (Princeton论文)

9种GEO内容优化策略(蒸馏自geo_functions.py):
  1. authoritative: 权威语气（断言式、自信）
  2. citing_credible: 引用可信来源（学术论文、官方数据）
  3. more_quotes: 整理已有真实引语
  4. stats_optimization: 强化已有真实数据
  5. technical_terms: 添加专业术语
  6. simple_language: 简化语言（降低认知负荷）
  7. unique_words: 使用独特/稀有词汇
  8. fluent: 提升文本流畅度
  9. seo_optimize: SEO关键词优化

论文核心发现: GEO优化可提升AI引用率40%

合规约束（2026-07 AI内容监管新规）:
- 禁止编造统计数据、编造专家引语、编造来源引用
- 禁止极限词（第一/最好/顶级等）
- 每次优化后过合规门禁(compliance_auditor)，违规项随结果返回
"""

import json
import logging
import requests
from config import MZY_API_KEY, MZY_BASE_URL, DEFAULT_MODEL
from agents.compliance_auditor import check_compliance

logger = logging.getLogger(__name__)

MODEL_TEMPS = {"kimi-k3": 1.0}

# 9种优化策略 (蒸馏自geo_functions.py)
STRATEGIES = {
    "authoritative": {
        "name": "权威语气",
        "description": "使用断言式、自信的语气，增强内容可信度",
        "instruction": "将以下内容改写为更具权威性的版本。使用断言式语气，避免模糊表达（如'可能'、'或许'），使用确定性表述。保持事实准确，但语气更加自信和专业。禁止使用极限词（'第一''最好''顶级''唯一'等），禁止添加原文没有的事实声明。",
    },
    "citing_credible": {
        "name": "引用可信来源",
        "description": "为已有论点标注内容中已提及的可信来源",
        "instruction": "梳理以下内容，为关键论点补充来源标注。只允许使用内容中已经提及的来源（官方数据、报告、标准等）；内容中没有的来源一律不得编造，可在文末用'【建议补充来源】'标记需要用户提供真实来源的论点。禁止虚构论文、报告、机构名称。",
    },
    "more_quotes": {
        "name": "真实引语整理",
        "description": "整理内容中已有的真实引语，无引语则标记待补充",
        "instruction": "梳理以下内容中已有的直接引语，规范其格式（引号+说话人身份）。禁止编造任何专家、学者、企业家的引语或观点。如果内容中没有引语，在适合引用真实客户/专家观点的位置用'【建议补充真实引语】'标记，由用户提供。",
    },
    "stats_optimization": {
        "name": "真实数据强化",
        "description": "强化内容中已有的真实数据，无数据则标记待补充",
        "instruction": "梳理以下内容中已有的数字、百分比、量化指标，将其放在更能支撑论点的位置并规范表述。禁止编造任何统计数据、行业平均数据、估算值。缺少数据支撑的论点用'【建议补充真实数据】'标记，由用户提供。",
    },
    "technical_terms": {
        "name": "专业术语",
        "description": "添加领域专业术语提升专业度",
        "instruction": "在以下内容中添加专业术语。识别内容所属领域，添加相关的专业术语和概念。术语应自然融入，不应过度堆砌。每个术语首次出现时附带简短解释。",
    },
    "simple_language": {
        "name": "简化语言",
        "description": "降低认知负荷，使内容更易被AI理解和引用",
        "instruction": "将以下内容简化为更易理解的版本。使用短句、主动语态、具体而非抽象的表述。降低认知负荷，使AI模型更容易提取和引用关键信息。保持核心信息不变。",
    },
    "unique_words": {
        "name": "独特词汇",
        "description": "使用独特/稀有词汇提升内容辨识度",
        "instruction": "将以下内容中使用独特或稀有词汇替代常见表达。选择在行业中使用但不泛滥的专业词汇，提升内容在AI生成中的辨识度。避免生僻到AI无法理解的程度。",
    },
    "fluent": {
        "name": "流畅度优化",
        "description": "提升文本连贯性和可读性",
        "instruction": "将以下内容改写为更流畅的版本。改善段落间的逻辑过渡，使用连接词增强连贯性。确保信息层次清晰，便于AI模型解析和引用。",
    },
    "seo_optimize": {
        "name": "SEO关键词优化",
        "description": "融入SEO关键词提升搜索引擎可见性",
        "instruction": "将以下内容进行SEO关键词优化。只融入与内容主题直接相关的核心关键词和长尾词，自然出现在文本中。禁止蹭无关热门词（如内容讲装修却堆'AI''大模型'），禁止重复堆砌品牌名/产品名。关键词密度控制在2-3%。",
    },
}


def _call_llm(prompt: str, model: str = None, temperature: float = None) -> str:
    model = model or DEFAULT_MODEL
    temp = temperature if temperature is not None else MODEL_TEMPS.get(model, 0.7)
    resp = requests.post(
        f"{MZY_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {MZY_API_KEY}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temp,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def apply_strategy(content: str, strategy_key: str, model: str = None) -> dict:
    """对内容应用单个GEO优化策略

    Args:
        content: 原始内容
        strategy_key: 策略key (见STRATEGIES)
        model: 使用的模型

    Returns:
        {"strategy": key, "name": name, "optimized_content": str, "content_length": int}
    """
    strategy = STRATEGIES.get(strategy_key)
    if not strategy:
        return {"error": f"未知策略: {strategy_key}"}

    prompt = f"""{strategy['instruction']}

原始内容：
{content}

请直接输出优化后的内容，不要添加任何解释或元信息。"""

    try:
        optimized = _call_llm(prompt, model=model, temperature=0.7)
    except Exception as e:
        logger.error("策略%s应用失败: %s", strategy_key, e)
        return {"strategy": strategy_key, "name": strategy["name"], "error": str(e)}

    compliance = check_compliance(optimized)
    result = {
        "strategy": strategy_key,
        "name": strategy["name"],
        "description": strategy["description"],
        "optimized_content": optimized,
        "original_length": len(content),
        "optimized_length": len(optimized),
        "compliance": {
            "risk_level": compliance["risk_level"],
            "total_violations": compliance["total_violations"],
            "violations": compliance["violations"][:10],
        },
    }
    if compliance["risk_level"] == "high":
        result["compliance_warning"] = "优化结果含高风险违规项（极限词/伪造背书/绝对化承诺），发布前必须修正"
    return result


def apply_all_strategies(content: str, model: str = None, selected: list = None) -> dict:
    """对内容应用多个GEO优化策略，返回对比结果

    Args:
        content: 原始内容
        selected: 选择的策略key列表，None=全部
    """
    keys = selected if selected else list(STRATEGIES.keys())
    results = {}
    for key in keys:
        results[key] = apply_strategy(content, key, model)
    return {
        "original_content": content,
        "strategies_applied": keys,
        "results": results,
    }


def get_strategies_info() -> list:
    """获取所有策略信息"""
    return [
        {"key": k, "name": v["name"], "description": v["description"]}
        for k, v in STRATEGIES.items()
    ]
