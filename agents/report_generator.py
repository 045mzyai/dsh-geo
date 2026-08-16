"""报告生成Agent - PDF报告导出 + 多模型并发探针 + 深度合成报告"""
import json
import io
import requests
from datetime import datetime
from config import MZY_API_KEY, MZY_BASE_URL, DEFAULT_MODEL
from models import get_db


class ReportGenerator:
    name = "ReportGenerator"
    description = "GEO报告生成：多模型并发探针、深度合成报告、PDF导出"

    PROBE_MODELS = {
        "deepseek-v4-pro": {"label": "DeepSeek V4 Pro"},
        "kimi-k3": {"label": "Kimi K3"},
        "glm-5.2": {"label": "智谱 GLM-5.2"},
        "minimax-m3": {"label": "MiniMax M3"},
        "hy3": {"label": "混元 H3"},
    }

    MODEL_TEMPS = {"kimi-k3": 1.0}

    PROBE_QUERIES = [
        "请介绍一下{company}",
        "{company}怎么样？靠谱吗？",
        "{company}的核心产品是什么？",
        "成都AI公司推荐",
        "AI网关聚合服务哪个好？",
        "大模型API统一接入平台有哪些？",
    ]

    def execute(self, data):
        action = data.get("action", "")
        if action == "probe":
            return self._multi_model_probe(data)
        elif action == "synthesize":
            return self._synthesize_report(data)
        elif action == "full_report":
            return self._full_report(data)
        elif action == "action_plan":
            return self._generate_action_plan(data)
        return {"success": False, "error": f"未知操作: {action}"}

    def _multi_model_probe(self, data):
        """多模型并发探针：用5个模型同时查询品牌信息"""
        company = data.get("company", "")
        if not company:
            return {"success": False, "error": "缺少company参数"}

        company_short = company.replace("有限公司", "").replace("科技", "").replace("有限", "")
        company_parts = [company, company_short, "MzyToken", "mzyai"]

        queries = [q.format(company=company) for q in self.PROBE_QUERIES]

        probe_results = {}
        for model_id, model_info in self.PROBE_MODELS.items():
            model_results = []
            temp = self.MODEL_TEMPS.get(model_id, 0.3)

            for query in queries[:4]:
                try:
                    resp = requests.post(
                        f"{MZY_BASE_URL}/chat/completions",
                        headers={"Authorization": f"Bearer {MZY_API_KEY}"},
                        json={
                            "model": model_id,
                            "messages": [{"role": "user", "content": query}],
                            "temperature": temp,
                        },
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        answer = resp.json()["choices"][0]["message"]["content"]
                        mentioned = any(part in answer for part in company_parts)
                        accuracy = self._assess_accuracy(answer, company_parts)
                        model_results.append({
                            "query": query,
                            "mentioned": mentioned,
                            "accuracy": accuracy,
                            "answer": answer,
                            "answer_length": len(answer),
                        })
                    else:
                        model_results.append({"query": query, "error": f"API {resp.status_code}"})
                except requests.RequestException as e:
                    model_results.append({"query": query, "error": str(e)[:100]})

            mention_count = sum(1 for r in model_results if r.get("mentioned"))
            total = len(model_results)
            probe_results[model_id] = {
                "label": model_info["label"],
                "results": model_results,
                "mention_count": mention_count,
                "total_queries": total,
                "display_rate": round(mention_count / total * 100, 1) if total > 0 else 0,
            }

        return {"success": True, "data": {"company": company, "probe_results": probe_results, "mode": "production"}}

    def _synthesize_report(self, data):
        """深度合成报告：将多模型探针结果汇总，用AI生成综合诊断报告"""
        company = data.get("company", "")
        probe_data = data.get("probe_data")
        company_id = data.get("company_id")

        if not probe_data:
            probe_result = self._multi_model_probe(data)
            if not probe_result["success"]:
                return probe_result
            probe_data = probe_result["data"]

        db_data = self._get_db_data(company_id) if company_id else {}

        prompt = self._build_synthesis_prompt(company, probe_data, db_data)

        try:
            resp = requests.post(
                f"{MZY_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {MZY_API_KEY}"},
                json={
                    "model": DEFAULT_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                report_content = resp.json()["choices"][0]["message"]["content"]
                return {"success": True, "data": {
                    "company": company,
                    "report_content": report_content,
                    "probe_summary": self._summarize_probe(probe_data),
                    "mode": "production",
                }}
            return {"success": False, "error": f"AI调用失败: {resp.status_code}"}
        except requests.RequestException as e:
            return {"success": False, "error": f"请求失败: {e}"}

    def _generate_action_plan(self, data):
        """30/60/90天行动计划生成（参考GEORank逻辑）"""
        company = data.get("company", "")
        company_id = data.get("company_id")
        diagnose_data = data.get("diagnose_data", {})

        db_data = self._get_db_data(company_id) if company_id else {}

        prompt = f"""你是一位GEO（生成式引擎优化）专家。请为{company}生成30/60/90天行动计划。

## 当前诊断数据
{json.dumps(db_data, ensure_ascii=False, indent=2) if db_data else '无诊断数据'}

## 诊断结果
{json.dumps(diagnose_data, ensure_ascii=False, indent=2) if diagnose_data else '无诊断结果'}

## 公司信息
- 名称：{company}
- 核心产品：MzyToken AI网关聚合服务，35+大模型统一API接入
- 位置：四川省成都市
- 资质：2025年国家级科技型中小企业

## 输出要求
请严格按以下JSON格式输出行动计划（不要输出其他内容）：

```json
{{
  "summary": {{
    "headline": "一句话总结",
    "overview": "120字内概述",
    "priority_action": "最优先行动"
  }},
  "strengths": ["优势1", "优势2", "优势3"],
  "gaps": ["差距1", "差距2", "差距3"],
  "phase_plan": [
    {{
      "phase": "P0",
      "period": "30天",
      "title": "紧急补齐基础信号",
      "goal": "阶段目标描述",
      "tasks": [
        {{"task": "任务描述", "owner": "负责人", "deliverable": "交付物", "metric": "验收指标", "priority": "high"}}
      ],
      "success_metric": "阶段验收指标"
    }},
    {{
      "phase": "P1",
      "period": "60天",
      "title": "增强AI可见性信号",
      "goal": "阶段目标描述",
      "tasks": [
        {{"task": "任务描述", "owner": "负责人", "deliverable": "交付物", "metric": "验收指标", "priority": "medium"}}
      ],
      "success_metric": "阶段验收指标"
    }},
    {{
      "phase": "P2",
      "period": "90天",
      "title": "持续补强引用与案例",
      "goal": "阶段目标描述",
      "tasks": [
        {{"task": "任务描述", "owner": "负责人", "deliverable": "交付物", "metric": "验收指标", "priority": "low"}}
      ],
      "success_metric": "阶段验收指标"
    }}
  ]
}}
```

P0（30天）= 紧急补齐缺失的关键信号（Organization Schema、meta description、llms.txt、联系方式页面）
P1（60天）= 增强AI可见性信号（FAQPage Schema、OG标签、权威引用、UGC内容）
P2（90天）= 持续优化（扩充案例、内部链接、长尾关键词、转化路径优化）

请确保每个阶段3-5个具体任务，每个任务有明确的负责人、交付物和验收指标。"""

        try:
            resp = requests.post(
                f"{MZY_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {MZY_API_KEY}"},
                json={
                    "model": DEFAULT_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 6000,
                },
                timeout=90,
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                plan = self._parse_json_from_response(content)
                return {"success": True, "data": {"company": company, "action_plan": plan, "raw_content": content, "mode": "production"}}
            return {"success": False, "error": f"AI调用失败: {resp.status_code}"}
        except requests.RequestException as e:
            return {"success": False, "error": f"请求失败: {e}"}

    def _full_report(self, data):
        """完整报告：多模型探针 + 深度合成 + 行动计划 + PDF数据"""
        company = data.get("company", "")
        company_id = data.get("company_id")

        probe_result = self._multi_model_probe(data)
        if not probe_result["success"]:
            return probe_result

        synthesize_data = {**data, "probe_data": probe_result["data"]}
        synth_result = self._synthesize_report(synthesize_data)

        db_data = self._get_db_data(company_id) if company_id else {}
        diagnose_data = data.get("diagnose_data", {})
        plan_data = {**data, "diagnose_data": diagnose_data}
        plan_result = self._generate_action_plan(plan_data)

        report = {
            "company": company,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "probe": probe_result["data"] if probe_result["success"] else None,
            "synthesis": synth_result["data"] if synth_result["success"] else None,
            "action_plan": plan_result["data"] if plan_result["success"] else None,
            "db_data": db_data,
        }

        return {"success": True, "data": report}

    def _get_db_data(self, company_id):
        if not company_id:
            return {}
        conn = get_db()
        try:
            company = conn.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
            report = conn.execute("SELECT * FROM geo_reports WHERE company_id=? ORDER BY created_at DESC LIMIT 1", (company_id,)).fetchone()
            metrics = conn.execute("SELECT * FROM geo_metrics WHERE company_id=?", (company_id,)).fetchall()
            issues = conn.execute("SELECT * FROM website_issues WHERE company_id=? ORDER BY severity", (company_id,)).fetchall()
            competitors = conn.execute("SELECT * FROM competitors WHERE company_id=?", (company_id,)).fetchall()
            tasks = conn.execute("SELECT * FROM optimization_tasks WHERE company_id=? ORDER BY roi_score DESC", (company_id,)).fetchall()

            return {
                "company": dict(company) if company else None,
                "report": dict(report) if report else None,
                "metrics": [dict(m) for m in metrics],
                "issues": [dict(i) for i in issues],
                "competitors": [dict(c) for c in competitors],
                "tasks": [dict(t) for t in tasks],
            }
        finally:
            conn.close()

    def _build_synthesis_prompt(self, company, probe_data, db_data):
        probe_summary = self._summarize_probe(probe_data)
        db_summary = ""
        if db_data:
            report = db_data.get("report", {})
            if report:
                db_summary = f"\n## 已有诊断数据\n- GEO评分: {report.get('score', 'N/A')}/130 ({report.get('grade', 'N/A')}级)\n- 核心问题: {report.get('core_issue', 'N/A')}\n- 核心优势: {report.get('core_advantage', 'N/A')}"

        return f"""你是一位GEO（生成式引擎优化）诊断专家。请根据以下多模型探针数据，为{company}生成一份综合GEO诊断报告。

## 多模型探针结果
{json.dumps(probe_summary, ensure_ascii=False, indent=2)}
{db_summary}

## 输出要求
请按以下结构输出报告：

### 一、诊断概要
- 综合GEO评级（A/B/C/D级）
- 核心发现（3条）
- 紧急行动项（3条）

### 二、各AI引擎表现分析
对每个AI引擎（DeepSeek/Kimi/GLM/MiniMax/混元），分析：
- 品牌是否被提及
- 提及内容的准确度
- 缺失的关键信息

### 三、信源体系评估
- S/A/B级信源分布
- 与竞品差距
- 信源建设优先级

### 四、优化建议
- 紧急（30天内必须完成）
- 重要（60天内完成）
- 持续（90天持续优化）

### 五、预期效果
- 30天后预期GEO评分提升
- 60天后预期展示率提升
- 90天后预期准确率提升

请基于数据给出具体、可执行的建议，不要泛泛而谈。"""

    def _summarize_probe(self, probe_data):
        summary = {}
        for model_id, model_data in probe_data.get("probe_results", {}).items():
            summary[model_id] = {
                "label": model_data["label"],
                "display_rate": model_data["display_rate"],
                "mention_count": model_data["mention_count"],
                "total_queries": model_data["total_queries"],
                "accuracy_distribution": {},
            }
            acc_dist = {}
            for r in model_data.get("results", []):
                if "accuracy" in r:
                    acc = r["accuracy"]
                    acc_dist[acc] = acc_dist.get(acc, 0) + 1
            summary[model_id]["accuracy_distribution"] = acc_dist
        return summary

    def _assess_accuracy(self, answer, company_parts):
        has_name = any(part in answer for part in company_parts)
        has_business = any(kw in answer for kw in ["API", "网关", "大模型", "接入", "AI"])
        has_location = any(kw in answer for kw in ["成都", "四川", "木子杨"])
        has_product = "MzyToken" in answer or "mzyai" in answer
        score = sum([has_name, has_business, has_location, has_product])
        if score >= 3:
            return "高"
        elif score >= 2:
            return "中"
        elif score >= 1:
            return "低"
        return "无"

    def _parse_json_from_response(self, content):
        """从AI回复中提取JSON"""
        if "```json" in content:
            start = content.index("```json") + 7
            end = content.index("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.index("```") + 3
            end = content.index("```", start)
            content = content[start:end].strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw": content}
