# GEO 平台商业化开发记录

> 2026-08-16 完成 Phase 1-5 全部功能开发

## Phase 1: 用户认证 + 多租户

### 后端
- **`auth.py`**（新建）：注册/登录/JWT token/bcrypt密码哈希/套餐限额检查
  - `register(email, password, name, company_name)` → 创建user + 默认company
  - `login(email, password)` → 验证bcrypt → 返回JWT token
  - `decode_token(token)` → 解码JWT payload
  - `check_plan_limit(user_id, limit_type)` → 检查套餐用量限额
  - 套餐：free / pro / enterprise，限额：企业数/月监控数/月报告数

- **`models.py`**（修改）：
  - 新增 `users` 表（id, email, password_hash, name, plan, created_at）
  - `companies` 表新增 `owner_id` 列（ALTER TABLE migration）

- **`app.py`**（修改）：
  - 双模式认证：`GEO_API_TOKEN` 服务间Token / JWT用户认证
  - 新路由：`/api/auth/register`、`/api/auth/login`、`/api/auth/me`
  - `companies` 列表按 `owner_id` 过滤
  - 企业创建检查套餐限额

### 前端
- 登录/注册页（tab切换，邮箱+密码+姓名+企业名）
- `localStorage` token存储
- 所有API请求带 `Authorization: Bearer <token>` header
- 401响应自动跳转登录页
- 侧边栏用户信息（姓名+套餐）+退出按钮

### 依赖
- `bcrypt==4.0.1`、`PyJWT==2.8.0`

---

## Phase 2: AI引擎可见性监控增强

### 后端
- `/api/monitor/history/<cid>` — 分页历史记录（page/per_page参数）
- `/api/monitor/visibility-score/<cid>` — 综合评分
  - 公式：展示率×0.5 + 准确率×0.3 + (100-负面率)×0.2
  - 等级：A≥80 / B≥70 / C≥60 / D≥40 / F<40

### 前端
- 监控页新增可见性评分卡片（大数字+等级badge+三维度指标）
- 监控历史表格（时间/展示率/准确率/提及/类型）
- 监控完成后自动刷新评分和历史

---

## Phase 3: 竞争对手追踪

### 后端
- `/api/competitors/<cid>` GET — 列表
- `/api/competitors/<cid>` POST — 添加竞品
- `/api/competitors/<comp_id>` PUT — 更新竞品
- `/api/competitors/<comp_id>` DELETE — 删除竞品
- `/api/competitors/compare/<cid>` — 声音份额+引用差距+排名分析

### 前端
- 新增"竞品追踪"导航页
- 声音份额条形图（本企业高亮accent色）
- GEO分/平均分/排名 三指标卡
- 竞品列表表格（名称/域名/GEO分/引用源/AI准确率/备注/操作）
- 添加竞品弹窗（modal）

---

## Phase 4: 自动化报告增强

### 后端
- `/api/report-history/<cid>` — 报告历史列表
- `/api/dashboard/<cid>` — 执行仪表板（GEO分/报告分/展示率/准确率/竞品数/任务数/快照数/趋势）
- `/api/report-csv/<cid>` — CSV导出监控历史

### 前端
- 报告页新增CSV导出按钮
- 报告历史表格（时间/评分/等级/查看）
- `exportPdf()` / `exportCsv()` 函数（带auth header的fetch下载）

---

## Phase 5: 订阅计费

### 后端
- `/api/billing/plans` — 三套餐信息
  - 免费版：0元/月，1企业/10监控/3报告
  - 专业版：999元/年，10企业/100监控/50报告
  - 企业版：2999元/年，不限企业/无限监控/无限报告
- `/api/billing/usage` — 当前用量+限额
- `/api/billing/upgrade` — 升级套餐+刷新token

### 前端
- 新增"套餐计费"导航页
- 用量进度条（企业数/月监控/月报告，超80%变红）
- 三套餐卡片对比（当前套餐高亮accent边框+角标）
- 升级按钮（确认后刷新token+更新侧边栏）

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `requirements.txt` | 修改 | +bcrypt +PyJWT |
| `auth.py` | 新建 | 认证模块 |
| `models.py` | 修改 | +users表 +owner_id列 |
| `app.py` | 修改 | +auth路由 +竞品CRUD +计费 +报告历史 +仪表板 +CSV |
| `static/index.html` | 修改 | +竞品追踪/套餐计费导航项 |
| `static/js/app.js` | 修改 | +auth状态 +登录/注册 +竞品页 +计费页 +报告历史 +可见性评分 |
| `static/css/style.css` | 修改 | +auth样式 +modal样式 |

## 新增API清单（15个）

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | /api/auth/register | 注册 |
| POST | /api/auth/login | 登录 |
| GET | /api/auth/me | 当前用户 |
| POST | /api/companies | 创建企业（带限额检查）|
| GET | /api/competitors/<cid> | 竞品列表 |
| POST | /api/competitors/<cid> | 添加竞品 |
| PUT | /api/competitors/<comp_id> | 更新竞品 |
| DELETE | /api/competitors/<comp_id> | 删除竞品 |
| GET | /api/competitors/compare/<cid> | 声音份额对比 |
| GET | /api/monitor/history/<cid> | 监控历史 |
| GET | /api/monitor/visibility-score/<cid> | 可见性评分 |
| GET | /api/report-history/<cid> | 报告历史 |
| GET | /api/dashboard/<cid> | 执行仪表板 |
| GET | /api/report-csv/<cid> | CSV导出 |
| GET | /api/billing/plans | 套餐列表 |
| GET | /api/billing/usage | 用量统计 |
| POST | /api/billing/upgrade | 升级套餐 |
