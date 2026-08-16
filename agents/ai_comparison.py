"""AI对比测试Agent — GDO实践：模拟客户签约前的AI决策验证场景

客户在联系企业后，会向AI提出三类决策问题：
1. 验证型："XX公司值得合作吗？"
2. 比较型："XX和YY公司选哪家？"
3. 方案审查型："这份报价/方案合理吗？"

本Agent模拟这些场景，帮助企业了解自己在AI决策环节的表现
"""
from __future__ import annotations
import json
import logging
from typing import Optional
import requests
from config import MZY_API_KEY, MZY_BASE_URL, DEFAULT_MODEL

logger = logging.getLogger(__name__)

DECISION_SCENARIOS = [
    {
        "key": "worth_cooperating",
        "name": "合作价值验证",
        "question_template": "{company}（{domain}）这家公司值得合作吗？请从公司实力、案例、服务流程、客户评价等方面分析。",
        "description": "客户联系企业后，向AI验证企业是否靠谱",
    },
    {
        "key": "comparison",
        "name": "竞品对比",
        "question_template": "我要在{company}（{domain}）和{competitor}之间选一家合作，请从案例、服务、价格、口碑等角度对比分析，给出建议。",
        "description": "客户让AI对比自己与竞争对手",
    },
    {
        "key": "case_credibility",
        "name": "案例可信度",
        "question_template": "{company}（{domain}）官网上展示的案例是否可信？请帮我分析这些案例的真实性和说服力。",
        "description": "客户让AI验证企业案例的真实性",
    },
    {
        "key": "quote_reasonableness",
        "name": "报价合理性",
        "question_template": "我收到了{company}（{domain}）的方案报价，请帮我分析这个报价是否合理，有哪些需要注意的点？",
        "description": "客户让AI审查企业报价是否合理",
    },
    {
        "key": "risk_assessment",
        "name": "合作风险评估",
        "question_template": "如果我和{company}（{domain}）合作，可能有哪些风险？请帮我分析合作前需要注意的事项。",
        "description": "客户让AI评估与企业的合作风险",
    },
]


def _call_llm(prompt: str, model: str = None) -> str:
    model = model or DEFAULT_MODEL
    resp = requests.post(
        f"{MZY_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {MZY_API_KEY}"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.5},
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _analyze_decision_response(response: str, company_name: str) -> dict:
    """分析AI回答中的情感倾向和关键信息"""
    positive_markers = ["值得", "推荐", "专业", "可靠", "优势", "实力", "经验丰富", "案例丰富", "流程完善", "口碑良好"]
    negative_markers = ["风险", "不足", "建议谨慎", "需要核实", "信息有限", "不太靠谱", "实力偏弱", "不建议", "缺乏", "缺失", "矛盾"]
    neutral_markers = ["建议进一步", "综合判断", "需要更多信息", "建议比较", "可以参考"]

    positive_count = sum(1 for m in positive_markers if m in response)
    negative_count = sum(1 for m in negative_markers if m in response)
    neutral_count = sum(1 for m in neutral_markers if m in response)

    if positive_count > negative_count + neutral_count:
        sentiment = "positive"
        sentiment_label = "正面"
    elif negative_count > positive_count:
        sentiment = "negative"
        sentiment_label = "负面"
    else:
        sentiment = "neutral"
        sentiment_label = "中性/保守"

    found_positive = [m for m in positive_markers if m in response]
    found_negative = [m for m in negative_markers if m in response]

    return {
        "sentiment": sentiment,
        "sentiment_label": sentiment_label,
        "positive_signals": found_positive,
        "negative_signals": found_negative,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "response_length": len(response),
    }


def run_decision_test(company_name: str, domain: str, competitor: str = "", scenarios: list = None, model: str = None) -> dict:
    """运行AI决策测试"""
    if scenarios is None:
        scenarios = [s["key"] for s in DECISION_SCENARIOS]

    scenario_map = {s["key"]: s for s in DECISION_SCENARIOS}
    results = []

    for scenario_key in scenarios:
        scenario = scenario_map.get(scenario_key)
        if not scenario:
            continue

        question = scenario["question_template"].format(
            company=company_name,
            domain=domain,
            competitor=competitor or "另一家同行业公司",
        )

        try:
            response = _call_llm(question, model)
        except Exception as e:
            logger.warning("AI决策测试 %s 失败: %s", scenario_key, e)
            results.append({
                "scenario": scenario_key,
                "scenario_name": scenario["name"],
                "question": question,
                "error": str(e),
            })
            continue

        analysis = _analyze_decision_response(response, company_name)

        results.append({
            "scenario": scenario_key,
            "scenario_name": scenario["name"],
            "description": scenario["description"],
            "question": question,
            "ai_response": response,
            "analysis": analysis,
        })

    positive_count = sum(1 for r in results if r.get("analysis", {}).get("sentiment") == "positive")
    negative_count = sum(1 for r in results if r.get("analysis", {}).get("sentiment") == "negative")
    neutral_count = sum(1 for r in results if r.get("analysis", {}).get("sentiment") == "neutral")

    if positive_count > negative_count:
        overall = "positive"
    elif negative_count > positive_count:
        overall = "negative"
    else:
        overall = "neutral"

    return {
        "company": company_name,
        "domain": domain,
        "competitor": competitor or None,
        "model": model or DEFAULT_MODEL,
        "scenarios": results,
        "summary": {
            "total": len(results),
            "positive": positive_count,
            "negative": negative_count,
            "neutral": neutral_count,
            "overall_sentiment": overall,
        },
    }


def get_scenarios() -> list:
    return [{"key": s["key"], "name": s["name"], "description": s["description"]} for s in DECISION_SCENARIOS]
