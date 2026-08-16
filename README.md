# dsh-geo

[![CI](https://github.com/045mzyai/dsh-geo/actions/workflows/ci.yml/badge.svg)](https://github.com/045mzyai/dsh-geo/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%20%7C%203.12-blue.svg)](https://www.python.org/)
[![GitHub stars](https://img.shields.io/github/stars/045mzyai/dsh-geo?style=social)](https://github.com/045mzyai/dsh-geo/stargazers)
[![last commit](https://img.shields.io/github/last-commit/045mzyai/dsh-geo)](https://github.com/045mzyai/dsh-geo/commits/main)
[![issues](https://img.shields.io/github/issues/045mzyai/dsh-geo)](https://github.com/045mzyai/dsh-geo/issues)

> 由 [妙智云](https://www.mzyai.com) 开源维护 · AI 驱动的新一代智能云平台
>
> 面向 AI 大模型时代的企业官网 **GEO（生成式引擎优化）** 平台 —— 让你的官网在 DeepSeek、Kimi、豆包、GLM、混元 等 AI 回答中被准确引用与推荐。

**English:** A self-hosted GEO (Generative Engine Optimization) platform for enterprise websites. Instead of ranking on traditional search engines, GEO optimizes your site so LLM-based answer engines accurately cite and recommend it. dsh-geo bundles diagnosis, multi-dimensional scoring, optimization-artifact generation, compliance gating, and AI-visibility benchmarking in one Flask service.

---

## ✨ 核心能力

| 能力 | 说明 |
|------|------|
| **企业入库** `geo_ingest` | 抓取并入库企业官网，提取品牌 / 产品 / 案例 / 联系信息 |
| **单页诊断** `geo_diagnose` | 单页 GEO 体检，返回 0–100 分、等级与问题清单 |
| **SHEEP 评分** `geo_sheep_score` | SHEEP 五维评分 + GEM 综合分（核心指标） |
| **优化产物生成** `geo_optimize` | 一键生成 `llms.txt` / `robots.txt` / `sitemap.xml` / meta / FAQ |
| **合规门禁** `geo_compliance_check` | 极限词 / 伪造背书 / 绝对化承诺 / 关键词堆砌检测，发布前硬性约束 |
| **AI 决策审计** `geo_*_auditor` | 审计 AI 决策证据、模拟 AI 引用查询 |
| **AI 监控** | 定时监测目标站点在多个 AI 模型中的可见性与引用变化 |
| **基准测试 / AB 测试** | 跨模型基准对比、优化前后 AB 测试套件 |
| **成熟度评分** | 全站 GEO 成熟度分层评估 |
| **RAG 对话** | 基于已入库企业知识的检索增强对话 |
| **报告生成** | PDF 体检报告、关键词扩展、内容策略生成、PDF 去重审计 |
| **多租户与计费** | 注册 / 登录 / JWT 鉴权，free / pro / enterprise 套餐限额 |

## 🧠 SHEEP / GEM 评分模型

GEM 综合分由五个维度加权得出：

| 维度 | 含义 | 关注点 |
|------|------|--------|
| **S** | 语义结构化 | Schema.org 标记、语义化 HTML、实体消歧 |
| **H** | 人机双读 | 内容既对人友好也对 AI 可解析 |
| **E1** | AI 生态融合 | `llms.txt`、`robots.txt` 对 AI 爬虫的可达性 |
| **E2** | AI 内容适配 | 内容是否便于大模型抽取、引用、总结 |
| **P** | 性能可访问 | 加载速度、可访问性、移动端适配 |

**等级**：A+ (≥90) / A (≥80) / B+ (≥75) / B (≥70) / C+ (≥65) / C (≥60) / D (<60)。

评分内置两个质量机制：
- **自洽性多采样**：每个维度多次采样取中位数共识，降低单次抖动。
- **证据锚定反思**：客观诊断信号（如 `llms.txt` 已部署）会约束 LLM 打分下限，发现矛盾触发重评。

## 🚦 GEO 合规红线

2026-07-15 AI 内容监管新规生效，行业从野蛮生长进入合规时代。以下规则高于一切优化技巧：

1. **禁止** AI 批量生成垃圾内容铺量 —— 质量优先。
2. **禁止** 关键词堆砌、蹭无关热门词 —— 实证：堆砌导致 AI 可见性 -8%。
3. **禁止** 虚假宣传、刷评价、抹黑竞品 —— 编造内容会被 AI 交叉验证识破。
4. **禁止** 冒充官方、伪造权威背书 —— 欺诈性质，监管重罚。

任何待发布内容（FAQ / 优化文案 / 策略改写结果）交付前必须通过 `geo_compliance_check`，`risk_level=high` 时修正后重检，禁止直接交付。

## 🏗️ 架构

```
dsh-geo/
├── app.py                 # Flask 后端入口 + 路由 + 鉴权中间件
├── auth.py                # 注册 / 登录 / JWT / 多租户 / 套餐限额
├── config.py              # 端口 / 模型路由 / 运行模式
├── models.py              # SQLite 数据层
├── agents/                # 业务编排 agent（诊断 / 评分 / 优化 / 合规 ...）
├── pi-agent/              # 开源 Pi agent 扩展（把平台封装为原生工具）
├── static/                # 前端 SPA（index.html / css / js）
├── templates/
├── cases/                 # 真实优化案例
├── data/                  # 案例输入 / 输出 JSON（示例数据）
├── tests/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env   # 填入 MZY_API_KEY（必填，AI 模型 API Key）

# 3. 启动服务
python app.py          # 默认 http://localhost:8060
```

打开浏览器访问 `http://localhost:8060`，按「快速上手」引导三步完成 GEO 体检。

## 🐳 Docker 部署

```bash
docker compose up -d   # 构建并后台启动
```

生产模式建议 `RUN_MODE=production` 并用 gunicorn（Dockerfile 已内置）。

## 🔐 环境变量

| 变量 | 必填 | 说明 |
|------|:----:|------|
| `MZY_API_KEY` | ✅ | AI 模型 API Key |
| `MZY_BASE_URL` | | AI 模型网关地址，默认 `https://token.mzyai.com/v1`；可替换为你自有的 OpenAI 兼容端点 |
| `GEO_JWT_SECRET` | | JWT 签名密钥（**生产务必覆盖默认值**） |
| `GEO_API_TOKEN` | | 服务间 Token；设置后所有 API 需 Bearer Token 鉴权 |
| `GEO_PORT` | | 监听端口，默认 `8060` |
| `GEO_DEBUG` | | 调试模式，默认 `true` |
| `RUN_MODE` | | `production` / `development` |

## 🔌 API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/health` | 平台健康检查 |
| POST | `/api/auth/register` `/api/auth/login` | 注册 / 登录 |
| POST | `/api/ingest` | 抓取并入库企业官网 |
| POST | `/api/diagnose` | 单页 GEO 诊断 |
| POST | `/api/sheep-score` | SHEEP 五维 + GEM 综合分 |
| POST | `/api/optimize` | 生成优化产物 |
| POST | `/api/compliance-check` | 内容合规门禁 |
| GET  | `/api/companies` `/api/cases` | 企业列表 / 案例对比 |
| …    | … | 完整路由见 `app.py` |

> **Agent 工具化**：`pi-agent/geo-extension.ts` 已把上述能力封装为 Pi agent 的原生工具，可在 AI 编排中直接调用。

## 📄 License

[MIT](./LICENSE) © 2026 [妙智云](https://www.mzyai.com)

## 🤝 贡献

欢迎 Issue / PR。请确保提交内容通过 `geo_compliance_check`，不包含极限词与未经证实的数据声明。

## ⚠️ 免责声明

本项目提供 GEO 优化工具与方法论，不鼓励任何违反所在地 AI 内容监管法规的用法。使用者的所有发布行为需自行承担合规责任。
