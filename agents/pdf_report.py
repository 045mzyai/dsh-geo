"""PDF报告生成 - 纯HTML转PDF方案，无需额外依赖"""
import os
import json
from datetime import datetime


def generate_report_html(report_data):
    """生成GEO诊断报告的HTML，浏览器可直接打印为PDF"""
    company = report_data.get("company", {})
    report = report_data.get("report", {})
    metrics = report_data.get("metrics", [])
    issues = report_data.get("issues", [])
    competitors = report_data.get("competitors", [])
    tasks = report_data.get("tasks", [])
    probe = report_data.get("probe", {})
    action_plan = report_data.get("action_plan", {})
    synthesis = report_data.get("synthesis", {})
    generated_at = report_data.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M"))

    score = report.get("score", 0) if report else 0
    grade = report.get("grade", "D") if report else "D"
    score_color = "#10b981" if score >= 70 else "#f59e0b" if score >= 40 else "#ef4444"

    # 指标表格
    metrics_rows = ""
    for m in metrics:
        val = m.get("metric_value", 0)
        val_color = "#10b981" if val >= 60 else "#f59e0b" if val >= 30 else "#ef4444"
        metrics_rows += f'<tr><td>{m.get("metric_name","")}</td><td style="color:{val_color};font-weight:700">{val}{m.get("metric_unit","")}</td><td style="color:#64748b">{m.get("source","")}</td></tr>'

    # 问题列表
    issues_rows = ""
    for i in issues:
        sev_color = {"fatal": "#ef4444", "high": "#f87171", "medium": "#f59e0b", "low": "#3b82f6"}.get(i.get("severity", ""), "#64748b")
        issues_rows += f'<tr><td style="color:{sev_color};font-weight:600">{i.get("severity","").upper()}</td><td>{i.get("title","")}</td><td style="color:#64748b;font-size:12px">{i.get("description","")}</td></tr>'

    # 竞品对比
    comp_rows = ""
    for c in competitors:
        comp_rows += f'<tr><td>{c.get("competitor_name","")}</td><td>{c.get("source_count",0)}条</td><td>{c.get("ai_accuracy",0)}%</td></tr>'

    # 优化任务
    task_rows = ""
    for t in tasks:
        roi = t.get("roi_score", 0)
        roi_color = "#10b981" if roi >= 7 else "#f59e0b" if roi >= 5 else "#64748b"
        task_rows += f'<tr><td style="color:{roi_color};font-weight:700">{roi}</td><td>{t.get("title","")}</td><td>{t.get("description","")}</td></tr>'

    # 多模型探针结果
    probe_section = ""
    if probe and probe.get("probe_results"):
        probe_rows = ""
        for model_id, model_data in probe.get("probe_results", {}).items():
            probe_rows += f'<tr><td>{model_data.get("label",model_id)}</td><td style="font-weight:700">{model_data.get("display_rate",0)}%</td><td>{model_data.get("mention_count",0)}/{model_data.get("total_queries",0)}</td></tr>'
        probe_section = f"""
        <div class="section">
            <h2>多模型AI探针结果</h2>
            <table><thead><tr><th>AI引擎</th><th>展示率</th><th>提及次数</th></tr></thead><tbody>{probe_rows}</tbody></table>
        </div>"""

    # 行动计划
    plan_section = ""
    if action_plan and action_plan.get("action_plan"):
        plan = action_plan["action_plan"]
        if isinstance(plan, dict):
            summary = plan.get("summary", {})
            phases = plan.get("phase_plan", [])
            plan_section = f"""
            <div class="section">
                <h2>30/60/90天行动计划</h2>
                <div class="summary-box">
                    <p><strong>核心发现：</strong>{summary.get("headline","")}</p>
                    <p><strong>最优先行动：</strong>{summary.get("priority_action","")}</p>
                </div>"""
            for phase in phases:
                phase_color = {"P0": "#ef4444", "P1": "#f59e0b", "P2": "#10b981"}.get(phase.get("phase",""), "#64748b")
                task_list = ""
                for task in phase.get("tasks", []):
                    task_list += f'<li><strong>{task.get("task","")}</strong> — 负责人: {task.get("owner","")} | 交付物: {task.get("deliverable","")} | 验收: {task.get("metric","")}</li>'
                plan_section += f"""
                <div class="phase-box" style="border-left:4px solid {phase_color}">
                    <h3 style="color:{phase_color}">{phase.get("phase","")} — {phase.get("period","")}：{phase.get("title","")}</h3>
                    <p style="color:#64748b">{phase.get("goal","")}</p>
                    <ul>{task_list}</ul>
                    <p style="color:{phase_color};font-weight:600">验收指标：{phase.get("success_metric","")}</p>
                </div>"""
            plan_section += "</div>"

    # 深度合成报告
    synth_section = ""
    if synthesis and synthesis.get("report_content"):
        synth_section = f"""
        <div class="section">
            <h2>AI深度合成诊断报告</h2>
            <div class="synth-content">{_markdown_to_html(synthesis["report_content"])}</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>GEO诊断报告 - {company.get('name','')}</title>
<style>
@page {{ size: A4; margin: 20mm; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: "Noto Sans SC", "Microsoft YaHei", sans-serif; color: #1a1a2e; line-height: 1.7; font-size: 13px; }}
.header {{ text-align: center; padding: 30px 0 20px; border-bottom: 3px solid #10b981; margin-bottom: 24px; }}
.header h1 {{ font-size: 24px; color: #0a0e17; margin-bottom: 4px; }}
.header .subtitle {{ color: #64748b; font-size: 13px; }}
.score-box {{ display: inline-block; text-align: center; padding: 16px 32px; border: 3px solid {score_color}; border-radius: 8px; margin: 16px 0; }}
.score-box .score {{ font-size: 48px; font-weight: 800; color: {score_color}; }}
.score-box .grade {{ font-size: 20px; color: {score_color}; font-weight: 700; }}
.section {{ margin-bottom: 24px; page-break-inside: avoid; }}
.section h2 {{ font-size: 16px; color: #0a0e17; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
th {{ text-align: left; padding: 8px 10px; background: #f1f5f9; border-bottom: 2px solid #e2e8f0; font-weight: 600; color: #475569; font-size: 11px; text-transform: uppercase; }}
td {{ padding: 8px 10px; border-bottom: 1px solid #e2e8f0; }}
.summary-box {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 12px 16px; margin-bottom: 12px; }}
.phase-box {{ background: #fafafa; border-radius: 6px; padding: 12px 16px; margin-bottom: 12px; }}
.phase-box h3 {{ font-size: 14px; margin-bottom: 6px; }}
.phase-box ul {{ padding-left: 20px; font-size: 12px; }}
.phase-box li {{ margin-bottom: 4px; }}
.synth-content {{ font-size: 12px; line-height: 1.8; }}
.synth-content h3 {{ font-size: 14px; margin: 12px 0 6px; color: #0a0e17; }}
.synth-content p {{ margin-bottom: 8px; }}
.synth-content ul {{ padding-left: 20px; margin-bottom: 8px; }}
.footer {{ text-align: center; color: #94a3b8; font-size: 11px; margin-top: 32px; padding-top: 12px; border-top: 1px solid #e2e8f0; }}
@media print {{ .no-print {{ display: none; }} }}
</style>
</head>
<body>
<div class="header">
    <h1>GEO诊断报告</h1>
    <div class="subtitle">{company.get('name','')} | {company.get('domain','')} | {company.get('industry','')} | {company.get('city','')}</div>
    <div class="score-box">
        <div class="score">{score}</div>
        <div class="grade">{grade}级</div>
    </div>
    <div class="subtitle">报告生成时间：{generated_at}</div>
</div>

<div class="section">
    <h2>核心问题</h2>
    <p>{report.get('core_issue','') if report else ''}</p>
</div>

<div class="section">
    <h2>核心指标</h2>
    <table><thead><tr><th>指标</th><th>数值</th><th>数据来源</th></tr></thead><tbody>{metrics_rows}</tbody></table>
</div>

<div class="section">
    <h2>网站问题</h2>
    <table><thead><tr><th>严重度</th><th>问题</th><th>说明</th></tr></thead><tbody>{issues_rows}</tbody></table>
</div>

<div class="section">
    <h2>竞品对标</h2>
    <table><thead><tr><th>竞品</th><th>信源量</th><th>准确率</th></tr></thead><tbody>{comp_rows}</tbody></table>
</div>

{probe_section}

{synth_section}

{plan_section}

<div class="section">
    <h2>优化任务清单（按ROI排序）</h2>
    <table><thead><tr><th>ROI</th><th>任务</th><th>说明</th></tr></thead><tbody>{task_rows}</tbody></table>
</div>

<div class="footer">
    GEO Platform 生成 | 木子杨科技 | 本报告由AI辅助生成，建议结合人工判断
</div>

<button class="no-print" onclick="window.print()" style="position:fixed;bottom:20px;right:20px;padding:12px 24px;background:#10b981;color:#fff;border:none;border-radius:6px;font-size:14px;cursor:pointer;font-weight:600">打印/PDF导出</button>
</body>
</html>"""
    return html


def _markdown_to_html(text):
    """简易Markdown转HTML"""
    if not text:
        return ""
    lines = text.split("\n")
    html_lines = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h3>{stripped[3:]}</h3>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{stripped[2:]}</li>")
        elif stripped.startswith(("1.", "2.", "3.", "4.", "5.")):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = stripped[3:] if len(stripped) > 2 else stripped
            html_lines.append(f"<li>{content}</li>")
        elif stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{stripped}</p>")
    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)
