# 贡献指南 | Contributing to dsh-geo

感谢你对 **dsh-geo** 的兴趣！本指南帮助你快速参与贡献。无论修复 Bug、新增 agent、完善文档还是补充案例，都欢迎提交。

## 📋 参与前请先了解

- **dsh-geo 是什么**：面向 AI 大模型时代的 GEO（生成式引擎优化）平台，让企业官网在 DeepSeek/Kimi/豆包/GLM/混元 等 AI 回答中被准确引用。详见 [README](./README.md)。
- **合规红线高于一切**：本项目遵循 2026-07 AI 内容监管新规。任何涉及文案、FAQ、优化产物的贡献，**必须通过 `geo_compliance_check`**，`risk_level=high` 时修正后重检，禁止直接合入。详见 README「GEO 合规红线」一节。
- **用数据说话**：结论须引用具体维度分、GEM 分、等级变化，不写空泛判断；区分相关与因果。

## 🛠️ 开发环境

```bash
# 1. 克隆（贡献者建议 fork 后克隆自己的副本）
git clone https://github.com/045mzyai/dsh-geo.git
cd dsh-geo

# 2. 创建虚拟环境（Python 3.8+）
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
pip install pytest          # 运行测试

# 4. 配置环境变量
cp .env.example .env       # 填入 MZY_API_KEY（AI 模型 API Key）
# MZY_BASE_URL 可替换为你自有的 OpenAI 兼容端点

# 5. 启动本地服务
python app.py               # http://localhost:8060
```

## ✅ 运行测试

```bash
python -m pytest tests/ -q      # 纯函数单测，无需真实 Key
```

CI（`.github/workflows/ci.yml`）会在 Python 3.8 / 3.12 上运行同一套测试；提交前请确保本地通过。

## 🔀 提交流程（Pull Request）

1. **Fork** 仓库并在新分支上开发：
   ```bash
   git checkout -b feat/your-feature
   ```
2. **提交** —— 请遵循 [Conventional Commits](https://www.conventionalcommits.org/)：
   | 前缀 | 用途 |
   |------|------|
   | `feat:` | 新功能 / 新 agent |
   | `fix:` | Bug 修复 |
   | `docs:` | 文档 |
   | `refactor:` | 重构（无行为变化） |
   | `test:` | 测试补充 |
   | `chore:` | 构建 / 依赖 / 杂项 |
   | `data:` | 案例数据 |
3. **本地测试通过**：`python -m pytest tests/ -q`。
4. **合规自检**：若改动涉及可发布内容，附上 `geo_compliance_check` 结果（`risk_level` 须为 `pass` 或 `medium` 及以下）。
5. **推送并开 PR**：目标分支 `main`，描述清楚动机与改动点。

维护者会在 CI 通过后 review；若需改动会直接在 PR 留言。

## 🧩 新增一个 agent

新 agent 放在 `agents/` 下，并在 `agents/__init__.py` 注册。建议：
- 纯逻辑尽量拆成可单测的私有函数（`_xxx`），并补充 `tests/test_core.py` 用例。
- 涉及网络的调用用 `unittest.mock.patch` 隔离（参考 `test_audit_duplicate_pdfs_with_mock`）。
- 返回结构保持 JSON 可序列化，便于前端与 Pi agent 工具消费。

## 🐛 报告 Issue

- 描述复现步骤、环境（Python 版本 / OS / 是否 Docker）、预期与实际行为。
- 涉及 AI 评分结果，请附上 `gem_score`、各维度分与诊断信号，便于定位。

## 📄 行为准则

- 友善、尊重、对事不对人。
- 不在 Issue / PR / 提交信息中泄露任何真实 API Key、客户隐私数据。
- 不提交违反所在地 AI 内容监管法规的内容。

## 📜 许可证

提交的贡献将依据仓库根目录的 [MIT License](./LICENSE) 发布。
