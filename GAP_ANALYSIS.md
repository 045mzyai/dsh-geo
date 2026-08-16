# GEO 平台商业化差距分析与功能补全方案

> 基于 2026-08-16 联网调研：竞品平台（Geoptie / OptimizeGEO / 艾奇GEO / 特比昂）+ GitHub 开源项目（GEO-optim/GEO 316星 / GeoRank 398星 / GEO-Optimizer-Skill 682星）+ 当前 geo.mzyai.com 平台盘点

---

## 一、当前平台已有能力盘点

### 已有且较强（保持即可）

| 模块 | 现状 | 评价 |
|------|------|------|
| **SHEEP 五维评分** | S/H/E1/E2/P 五维 + GEM 综合分 + 自洽性多采样 + 证据锚定反思 | 独特方法论，优于竞品的单一"可见性评分" |
| **网站诊断引擎** | `/api/diagnose` 抓取页面 → 结构化分析 → 客观诊断信号 | 功能完整，但缺少自动化持续监控 |
| **合规检测** | `agents/compliance_auditor.py` 规则引擎，4类风险，零LLM成本 | 行业领先，竞品大多无此能力 |
| **Pi Agent 编排** | `geo-extension.ts` 8个GEO工具 + AGENTS.md 领域知识 | 技术先进，但面向开发者不面向SaaS用户 |
| **RAG 知识问答** | SSE流式输出 + 向量检索 | 有基础能力 |
| **基准测试** | `/api/benchmark` 异步快照对比 | 有基础能力 |
| **前端SPA** | 21个页面，原生JS | 有基础UI |

### 已有但需增强

| 模块 | 现状 | 差距 |
|------|------|------|
| **内容优化建议** | `/api/optimize` 返回优化策略 | 缺少页面级可操作建议（具体改哪行代码、加什么Schema） |
| **案例库** | `/api/cases` 2家公司 | 数据量太少，需批量案例库 |
| **成熟度评分** | `/api/maturity/score` | 缺少行业基准对比 |
| **GDO审计** | `/api/gdo/audit` | 功能存在但前端曝光不足 |

---

## 二、商业化缺失功能（按优先级排序）

### P0 — 没有这些无法商业化（必须先做）

#### 1. 用户认证与多租户
- **现状**：无用户系统，无登录，无租户隔离
- **竞品参考**：所有商业平台都有（Geoptie / OptimizeGEO / GeoRank 后台管理）
- **需要**：
  - 用户注册/登录（手机号/邮箱/微信扫码）
  - 多租户数据隔离（每家企业看自己的数据）
  - 基于角色的权限控制（管理员/操作员/查看者）
  - API Key 管理（每租户独立Key）
- **技术方案**：SQLite 加 `users` / `tenants` / `user_tenants` / `api_keys` 表；JWT 认证中间件

#### 2. 订阅计费系统
- **现状**：无任何付费机制
- **竞品参考**：Geoptie 按追踪查询数量定价；OptimizeGEO 定制报价；艾奇GEO 梯度化产品
- **需要**：
  - 套餐定义（免费版/标准版/专业版/企业版）
  - 按月/按年订阅
  - 微信支付/支付宝接入
  - 用量计量（诊断次数/监控关键词数/报告数）
  - 套餐限制与超额提醒
- **技术方案**：`subscriptions` / `orders` / `usage_records` 表；支付网关对接

#### 3. AI 引擎可见性监控（核心差异化功能）
- **现状**：无实际向 AI 引擎发送查询并追踪品牌提及的能力
- **竞品参考**：Geoptie 的 Rank Tracker + AI Visibility Checker；OptimizeGEO 的可见性评分 + 声音份额；GEO-Optimizer-Skill 的 `geo citations` 命令
- **需要**：
  - 向 DeepSeek / Kimi / 豆包 / 文心一言 / 通义千问 / ChatGPT 发送预设提示词
  - 解析 AI 回答，检测品牌是否被提及/引用
  - 追踪可见性评分（被提及率）、引用频率、情感倾向、平均位置
  - 可视化趋势图表（按天/周/月）
  - 提示词矩阵管理（按业务场景分组）
- **技术方案**：`monitors` / `monitor_queries` / `monitor_results` 表；定时任务调度；LLM 网关调用

#### 4. 竞争对手追踪
- **现状**：无竞品对比功能
- **竞品参考**：Geoptie Competitive Radar；OptimizeGEO 竞争对手对比 + 可见性差距分析
- **需要**：
  - 添加竞争对手域名
  - 在同一提示词集下对比品牌 vs 竞品的可见性
  - 声音份额报告（按主题/AI平台/时间段）
  - 引用差距分析（竞品被引用而自身未被引用的查询）
  - 竞品 Schema 和结构化数据审计
- **技术方案**：`competitors` / `competitor_results` 表；复用监控引擎

#### 5. 自动化报告与导出
- **现状**：无报告生成功能
- **竞品参考**：所有平台都有执行仪表板 + PDF/Excel导出
- **需要**：
  - 月度 GEO 记分卡（自动生成）
  - 执行层仪表板（高级趋势 + ROI + 竞争定位）
  - 技术团队报告（具体页面 + Schema代码片段 + 优先级排名）
  - 导出 PDF / Excel / PowerPoint
  - 定时邮件推送
- **技术方案**：`reports` / `report_templates` 表；Jinja2 报告模板；定时任务

### P1 — 商业化竞争力（第二批做）

#### 6. llms.txt / JSON-LD 生成器工具
- **现状**：平台能诊断客户网站的 llms.txt 和 Schema，但不能帮客户生成
- **竞品参考**：GeoRank 的 GEO工具模块（JSON-LD生成器 + llms.txt生成器）；GEO-Optimizer-Skill 的 `geo fix` / `geo llms` / `geo schema` 命令
- **需要**：
  - 输入网站URL → 自动生成 llms.txt
  - 输入业务信息 → 生成 Organization / FAQPage / HowTo / Article / Product 等 JSON-LD
  - Schema 验证器（检查现有JSON-LD是否正确）
  - 一键部署指导
- **技术方案**：新增 `/api/tools/llms-txt` / `/api/tools/schema` 端点

#### 7. 关键词/提示词拓词工作台
- **现状**：无关键词研究功能
- **竞品参考**：GeoRank 拓词工作台（业务词→问题词→场景词→商业意图词）；Geoptie Keyword Finder
- **需要**：
  - 从业务关键词扩展到 AI 搜索提示词
  - 问题词（"XX怎么做"）、场景词（"XX场景下用什么"）、对比词（"XX vs YY"）
  - 提示词分组管理（按业务线/产品/场景）
  - 批量导入到监控矩阵
- **技术方案**：`keyword_groups` / `keywords` 表；LLM 辅助扩展

#### 8. 内容衰减检测
- **现状**：无内容新鲜度监控
- **竞品参考**：GEO-Optimizer-Skill v4.7 内容衰减预测（时间/统计/版本/事件/价格衰减）
- **需要**：
  - 检测页面内容的时效性（统计数据过时、价格变更、事件结束）
  - 常青评分（0-100，越高越不需要更新）
  - 更新提醒（哪些页面需要刷新数据）
- **技术方案**：定时抓取 + LLM 分析内容新鲜度

#### 9. AI 爬虫活动监控
- **现状**：无服务器日志分析
- **竞品参考**：GEO-Optimizer-Skill `geo logs` 命令；GEO 60项检查清单第2/44项
- **需要**：
  - 解析服务器访问日志，识别 AI 爬虫（GPTBot / ClaudeBot / PerplexityBot / GoogleOther / Bytespider）
  - 爬虫访问频率/页面覆盖率趋势
  - 未被爬虫访问的页面告警
- **技术方案**：日志解析模块 + `crawler_activity` 表

#### 10. 公开 API 与集成
- **现状**：有API但无文档、无速率限制、无Key管理
- **竞品参考**：OptimizeGEO API访问；GEO-Optimizer-Skill MCP服务器 + Python SDK + CLI
- **需要**：
  - API 文档（OpenAPI/Swagger）
  - API Key 认证 + 速率限制
  - Webhook 回调（监控完成通知）
  - SDK / CLI 工具
- **技术方案**：Flask-RESTX / flasgger 自动文档；Redis 速率限制

### P2 — 增强体验（后续迭代）

#### 11. 多平台内容发布建议
- **现状**：GEO领域知识中有"豆包→头条系、Kimi→知乎系"的偏好，但未产品化
- **需要**：根据目标AI引擎推荐内容发布平台

#### 12. 行业基准数据库
- **现状**：有基准测试框架但无行业数据
- **需要**：按行业积累SHEEP评分基准，供客户对比

#### 13. 多模态内容就绪检测
- **竞品参考**：GEO-Optimizer-Skill 多模态就绪（图片alt覆盖、VideoObject/AudioObject schema）
- **需要**：检测图片alt文本、视频字幕/转录文本、结构化数据覆盖

#### 14. 提示注入检测
- **竞品参考**：GEO-Optimizer-Skill 8种操纵模式检测
- **需要**：检测隐藏文本、不可见Unicode、LLM指令注入等作弊行为

---

## 三、竞品功能对比矩阵

| 功能 | geo.mzyai.com | Geoptie | OptimizeGEO | GeoRank(开源) | GEO-Optimizer(开源) |
|------|:---:|:---:|:---:|:---:|:---:|
| 网站诊断 | 有 | 有 | 无 | 有 | 有 |
| SHEEP五维评分 | 有(独有) | 无 | 无 | 无 | 无(8类100分制) |
| 合规检测 | 有(独有) | 无 | 无 | 无 | 无 |
| AI可见性监控 | 无 | 有 | 有 | 无 | 有(CLI) |
| 竞品追踪 | 无 | 有 | 有 | 无 | 无 |
| 引用追踪 | 无 | 有 | 有 | 无 | 有(CLI) |
| 声音份额 | 无 | 有 | 有 | 无 | 无 |
| llms.txt生成器 | 无 | 无 | 有 | 有 | 有 |
| JSON-LD生成器 | 无 | 无 | 无 | 有 | 有 |
| 关键词拓词 | 无 | 有 | 无 | 有 | 无 |
| 内容优化建议 | 有(基础) | 有 | 有 | 有 | 有 |
| 报告导出 | 无 | 有 | 有 | 无 | 有(HTML/SARIF) |
| 用户认证 | 无 | 有 | 有 | 有 | 无 |
| 多租户 | 无 | 有 | 有 | 有 | 无 |
| 订阅计费 | 无 | 有 | 有 | 无 | 无 |
| API开放 | 无 | 有 | 有 | 无 | 有(MCP/CLI) |
| Pi Agent编排 | 有(独有) | 无 | 无 | 无 | 无 |
| RAG问答 | 有 | 无 | 无 | 有 | 无 |
| 内容衰减检测 | 无 | 无 | 无 | 无 | 有 |
| AI爬虫监控 | 无 | 无 | 无 | 无 | 有(CLI) |
| 提示注入检测 | 无 | 无 | 无 | 无 | 有 |
| 多模态就绪 | 无 | 无 | 无 | 无 | 有 |
| GitHub Action | 无 | 无 | 无 | 无 | 有 |

---

## 四、开源项目可借鉴/集成清单

| 开源项目 | Stars | 可借鉴点 | 集成方式 |
|---------|-------|---------|---------|
| **GEO-Optimizer-Skill** | 682 | 8类100分制评分体系、Citability 47维评分、llms.txt/schema生成器、AI爬虫日志分析、内容衰减检测、提示注入检测、MCP服务器 | `pip install geo-optimizer-skill` 作为依赖库调用 |
| **GeoRank** | 398 | 全流程设计（发现→诊断→问答→规划→拓展→结构化→管理）、拓词工作台、公司目录、专家/教程频道 | 参考架构设计，不直接集成（技术栈不同） |
| **GEO-optim/GEO** | 316 | GEO-Bench 基准测试数据集、优化函数定义 | 参考评测方法论，HuggingFace数据集可直接加载 |
| **AutoGEO** | 196 | 自动学习生成引擎偏好、自动重写网页内容 | 参考研究方向（ICLR'26论文） |

---

## 五、商业化功能补全路线图

### 阶段一：SaaS化基础（2-3周）
1. 用户认证 + 多租户
2. 订阅计费（微信支付）
3. API Key 管理
4. 前端改造（登录页 / 仪表板 / 套餐选择）

### 阶段二：核心监控能力（3-4周）
5. AI 引擎可见性监控（DeepSeek/Kimi/豆包/文心/通义/ChatGPT）
6. 提示词矩阵管理
7. 竞争对手追踪
8. 可见性趋势图表

### 阶段三：工具与报告（2-3周）
9. llms.txt / JSON-LD 生成器
10. 关键词拓词工作台
11. 自动化报告 + PDF导出
12. 执行仪表板

### 阶段四：增强与集成（2-3周）
13. 集成 GEO-Optimizer-Skill（pip依赖）
14. AI 爬虫活动监控
15. 内容衰减检测
16. 公开 API + 文档

### 阶段五：差异化（持续迭代）
17. 多平台内容发布建议
18. 行业基准数据库
19. 多模态就绪检测
20. 提示注入检测

---

## 六、技术架构建议

### 当前架构
```
浏览器 → nginx(443) → Flask(8060) → SQLite
                         |
                    LLM网关(token.mzyai.com)
```

### 商业化目标架构
```
浏览器 → nginx(443) → Flask(8060) → SQLite/PostgreSQL
                         |                    |
                    LLM网关              Redis(缓存+限流)
                    (token.mzyai.com)          |
                         |               定时任务调度
                    AI引擎监控            (APScheduler)
                    (DeepSeek/Kimi/
                     豆包/文心/通义)
                         |
                    监控结果存储
                    + 趋势分析
                    + 报告生成
```

### 数据库表新增（SQLite阶段）
```sql
-- 用户与租户
users (id, email, phone, password_hash, created_at)
tenants (id, name, plan_type, created_at)
user_tenants (user_id, tenant_id, role)
api_keys (id, tenant_id, key_hash, rate_limit, created_at)

-- 订阅计费
subscriptions (id, tenant_id, plan, start_date, end_date, status)
orders (id, tenant_id, amount, payment_method, payment_status, created_at)
usage_records (id, tenant_id, resource_type, count, period)

-- AI监控
monitors (id, tenant_id, name, status, created_at)
monitor_queries (id, monitor_id, prompt, category, ai_engine)
monitor_results (id, query_id, result_text, brand_mentioned, citation_found, sentiment, position, created_at)

-- 竞品
competitors (id, tenant_id, domain, name)
competitor_results (id, competitor_id, query_id, mentioned, cited, created_at)

-- 报告
reports (id, tenant_id, type, period, data_json, created_at)
report_templates (id, name, template_html)

-- 关键词
keyword_groups (id, tenant_id, name, type)
keywords (id, group_id, keyword, search_volume, intent)
```

---

## 七、定价策略建议（参考竞品）

| 套餐 | 月费 | 诊断次数 | 监控关键词 | 竞品数 | 报告 | API |
|------|------|---------|-----------|--------|------|-----|
| 免费版 | 0元 | 3次/月 | 5个 | 1个 | 基础 | 无 |
| 标准版 | 999元 | 50次/月 | 50个 | 3个 | 月度 | 无 |
| 专业版 | 2,999元 | 不限 | 200个 | 10个 | 周/月 | 有 |
| 企业版 | 9,999元 | 不限 | 不限 | 不限 | 自定义 | 有 |

---

## 八、核心结论

当前 geo.mzyai.com 平台在**评分方法论**（SHEEP五维）和**合规检测**方面有独特优势，但在**SaaS基础设施**（认证/计费/多租户）和**核心监控能力**（AI可见性追踪/竞品分析/报告）方面存在重大缺失。

**商业化优先级**：先补 SaaS 基础设施（认证+计费），再补核心监控能力（AI可见性+竞品追踪），最后补工具和报告。可集成 `geo-optimizer-skill`（682星 MIT协议）快速获得 llms.txt/schema生成、AI爬虫日志分析、内容衰减检测等能力，避免重复造轮子。
