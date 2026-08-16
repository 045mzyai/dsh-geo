"""GDO决策证据审计Agent — 蒸馏自郝攀六层全域增长模型第六层

GDO = Generative Decision Optimization，生成式决策优化
核心：客户找上门后，AI仍参与比较/验证/谈判，企业需把"销售话术里的能力"变成"AI可验证的决策证据"

审计5类决策证据：
1. 案例详情完整度（背景/问题/方案/过程/结果）
2. 服务流程透明度（交付/售后/问题处理）
3. 差异化定位清晰度（擅长什么/不擅长什么/适合谁）
4. 第三方信源覆盖度（媒体报道/客户评价/行业资料）
5. 证据链一致性（官网/第三方/自媒体信息是否矛盾）
"""
from __future__ import annotations
import json
import logging
from typing import Optional
import requests
from config import MZY_API_KEY, MZY_BASE_URL, DEFAULT_MODEL

logger = logging.getLogger(__name__)

EVIDENCE_DIMENSIONS = [
    {
        "key": "case_detail",
        "name": "案例详情",
        "description": "项目背景、客户问题、解决方案、执行过程、最终结果",
        "weight": 25,
        "check_items": [
            "案例是否包含项目背景（客户是谁、什么行业）",
            "案例是否描述客户具体问题或痛点",
            "案例是否说明解决方案的核心思路",
            "案例是否包含执行过程和关键节点",
            "案例是否有可量化的最终结果（数据指标）",
            "案例数量是否覆盖主要业务线（≥3个行业）",
        ],
    },
    {
        "key": "service_process",
        "name": "服务流程",
        "description": "交付流程、售后机制、问题处理机制",
        "weight": 20,
        "check_items": [
            "是否有公开的交付流程说明（阶段划分）",
            "是否说明项目周期和里程碑",
            "是否有售后机制说明（响应时间/处理流程）",
            "是否有问题处理和升级机制",
            "是否说明客户需要配合的事项",
            "是否有效果验收标准",
        ],
    },
    {
        "key": "differentiation",
        "name": "差异化定位",
        "description": "擅长什么、不擅长什么、适合什么客户、不适合什么项目",
        "weight": 20,
        "check_items": [
            "是否明确说明核心优势和差异化标签",
            "是否说明适合的客户类型（行业/规模）",
            "是否说明不适合的客户或项目类型",
            "是否说明服务边界（什么不做）",
            "团队/资质信息是否公开可查",
            "定价模式是否透明或有说明",
        ],
    },
    {
        "key": "third_party",
        "name": "第三方信源",
        "description": "媒体报道、客户评价、行业资料、专业社区",
        "weight": 20,
        "check_items": [
            "是否有媒体公开报道（非自媒发布）",
            "是否有客户评价或口碑内容",
            "是否有行业资料或白皮书引用",
            "是否有专业社区讨论（知乎/行业论坛）",
            "是否有工商资质/认证信息可查",
            "是否有合作伙伴或客户背书",
        ],
    },
    {
        "key": "evidence_chain",
        "name": "证据链一致性",
        "description": "官网/第三方/自媒体信息是否矛盾",
        "weight": 15,
        "check_items": [
            "官网描述与第三方信息是否一致",
            "案例信息在不同平台是否一致",
            "团队信息是否可交叉验证",
            "业务范围描述是否一致",
            "联系方式是否多渠道可查",
        ],
    },
]

GDO_SYSTEM_PROMPT = """你是GDO（生成式决策优化）审计专家。基于六层全域AI营销增长模型第六层理论。

你的任务是：审计企业在"AI可验证决策证据"方面的完整度。

当客户在签约前向AI询问"XX公司值得合作吗"、"XX和YY公司选哪家"时，AI需要找到足够的决策证据来回答。

审计5个维度：
1. 案例详情（25%）：项目背景/客户问题/解决方案/执行过程/最终结果
2. 服务流程（20%）：交付流程/售后机制/问题处理
3. 差异化定位（20%）：擅长什么/不擅长什么/适合谁
4. 第三方信源（20%）：媒体报道/客户评价/行业资料
5. 证据链一致性（15%）：官网/第三方/自媒体信息是否矛盾

返回JSON：
{
  "dimensions": [
    {
      "key": "维度key",
      "name": "维度名",
      "score": 0-100整数,
      "found_items": ["已满足的检查项"],
      "missing_items": ["未满足的检查项"],
      "evidence": ["找到的具体证据描述"],
      "suggestions": ["改进建议"]
    }
  ],
  "overall_score": 0-100整数,
  "level": "S/A/B/C/D",
  "summary": "总体评价",
  "critical_gaps": ["最关键的缺口，影响AI决策验证"],
  "priority_actions": ["按优先级排序的行动建议"]
}

评分标准：
- 90-100: S级，决策证据充分，AI可全面验证
- 80-89: A级，大部分证据完整，个别缺口
- 70-79: B级，有基础证据，但关键维度有缺口
- 60-69: C级，证据不足，AI回答会偏保守
- <60: D级，证据严重缺失，AI可能给出负面评价

重要：基于提供的网站诊断数据和公司信息进行审计，不编造不存在的信息。找不到的证据标记为missing。"""


def _call_llm(prompt: str, model: str = None) -> str:
    model = model or DEFAULT_MODEL
    resp = requests.post(
        f"{MZY_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {MZY_API_KEY}"},
        json={"model": model, "messages": [{"role": "system", "content": GDO_SYSTEM_PROMPT}, {"role": "user", "content": prompt}], "temperature": 0.3},
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _build_audit_input(company_name: str, domain: str, industry: str = "", diagnosis_data: dict = None, keywords: list = None, benchmark_data: dict = None) -> str:
    parts = [f"公司名称：{company_name}", f"官网：{domain}"]
    if industry:
        parts.append(f"行业：{industry}")

    if diagnosis_data:
        parts.append(f"\n网站诊断数据：")
        parts.append(f"  诊断评分：{diagnosis_data.get('score', 'N/A')}")
        checks = diagnosis_data.get("checks", {})
        if checks:
            meta = checks.get("meta_tags", {})
            parts.append(f"  Title标签：{meta.get('title', 'N/A')}")
            parts.append(f"  Description：{meta.get('description', 'N/A')}")
            sd = checks.get("structured_data", {})
            parts.append(f"  结构化数据JSON-LD数量：{sd.get('json_ld_count', 0)}")
            ai_read = checks.get("ai_readability", {})
            parts.append(f"  页面文本长度：{ai_read.get('text_length', 0)}字符")
            parts.append(f"  H1标签：{ai_read.get('h1_count', 0)}个")
            parts.append(f"  H2标签：{ai_read.get('h2_count', 0)}个")
            links = checks.get("links", {})
            parts.append(f"  内部链接：{links.get('internal_count', 0)}个")
            parts.append(f"  外部链接：{links.get('external_count', 0)}个")
            llms = checks.get("llms_txt", {})
            parts.append(f"  llms.txt：{'存在' if llms.get('exists') else '不存在'}")

    if keywords:
        parts.append(f"\n已扩展关键词（Top10）：{', '.join([k.get('keyword', k.get('expanded_keyword', '')) for k in keywords[:10]])}")

    if benchmark_data:
        parts.append(f"\nGEO基准测试：")
        parts.append(f"  AI引用率：{benchmark_data.get('citation_rate', 'N/A')}")
        parts.append(f"  平均排名：{benchmark_data.get('avg_rank', 'N/A')}")

    parts.append(f"\n审计维度和检查项：")
    for dim in EVIDENCE_DIMENSIONS:
        parts.append(f"\n{dim['name']}（权重{dim['weight']}%）：{dim['description']}")
        for item in dim["check_items"]:
            parts.append(f"  - {item}")

    return "\n".join(parts)


def _parse_audit_result(raw: str) -> dict:
    start, end = raw.find("{"), raw.rfind("}") + 1
    if start < 0 or end <= start:
        return {"error": "AI返回格式异常", "raw": raw[:500]}
    try:
        payload = json.loads(raw[start:end])
    except json.JSONDecodeError:
        return {"error": "AI返回JSON解析失败", "raw": raw[:500]}

    dimensions = payload.get("dimensions", [])
    for dim in dimensions:
        dim.setdefault("score", 0)
        dim.setdefault("found_items", [])
        dim.setdefault("missing_items", [])
        dim.setdefault("evidence", [])
        dim.setdefault("suggestions", [])

    overall = payload.get("overall_score", 0)
    level = payload.get("level", "D")
    if not level:
        if overall >= 90:
            level = "S"
        elif overall >= 80:
            level = "A"
        elif overall >= 70:
            level = "B"
        elif overall >= 60:
            level = "C"
        else:
            level = "D"

    return {
        "dimensions": dimensions,
        "overall_score": overall,
        "level": level,
        "summary": payload.get("summary", ""),
        "critical_gaps": payload.get("critical_gaps", []),
        "priority_actions": payload.get("priority_actions", []),
    }


def audit_decision_evidence(company_name: str, domain: str, industry: str = "", diagnosis_data: dict = None, keywords: list = None, benchmark_data: dict = None, model: str = None) -> dict:
    prompt = _build_audit_input(company_name, domain, industry, diagnosis_data, keywords, benchmark_data)
    try:
        raw = _call_llm(prompt, model)
    except Exception as e:
        logger.warning("GDO审计AI调用失败: %s", e)
        return {"error": f"AI调用失败: {e}"}

    result = _parse_audit_result(raw)
    result["model"] = model or DEFAULT_MODEL
    return result


def get_dimensions() -> list:
    return [{"key": d["key"], "name": d["name"], "description": d["description"], "weight": d["weight"], "check_items": d["check_items"]} for d in EVIDENCE_DIMENSIONS]


def simulate_ai_decision_query(company_name: str, domain: str, competitor: str = "", model: str = None) -> dict:
    """模拟客户在签约前向AI提出的决策问题"""
    if competitor:
        prompt = f"客户正在比较两家公司，请模拟AI的回答：\n\n问题：{company_name}（{domain}）和{competitor}相比，应该选择哪一家？请从案例、服务流程、差异化定位、第三方评价等角度分析。\n\n请给出客观分析，指出两家各自的优势和不足。"
    else:
        prompt = f"客户已经联系了{company_name}（{domain}），正在考虑是否签约。请模拟AI的回答：\n\n问题：{company_name}（{domain}）值得合作吗？请从案例、服务流程、差异化定位、第三方评价等角度分析。\n\n请给出客观评价，指出优势和风险。"

    try:
        raw = _call_llm(prompt, model)
    except Exception as e:
        return {"error": f"AI调用失败: {e}"}

    return {
        "question": f"{'对比' if competitor else '验证'}：{company_name}" + (f" vs {competitor}" if competitor else ""),
        "ai_response": raw,
        "model": model or DEFAULT_MODEL,
        "scenario": "comparison" if competitor else "validation",
    }
