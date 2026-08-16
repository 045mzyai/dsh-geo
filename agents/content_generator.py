"""GEO内容生成Agent - 生成AI搜索友好的内容"""
import json
from config import AI_CONFIG, MZY_API_KEY, MZY_BASE_URL, DEFAULT_MODEL
from agents.compliance_auditor import check_compliance

MODEL_TEMPS = {
    "kimi-k3": 1.0,
    "kimi-k2.5": 1.0,
    "kimi-k2.7-code": 1.0,
}
import requests


class ContentGenerator:
    name = "ContentGenerator"
    description = "GEO内容生成：生成AI搜索友好的FAQ、文章、教程等内容"

    CONTENT_TEMPLATES = {
        "faq": {
            "structure": "Q&A格式，每个问题独立，答案简洁完整",
            "ai_tips": "问题用自然语言表述，答案包含关键实体和事实",
        },
        "about": {
            "structure": "公司介绍+团队+资质+联系方式",
            "ai_tips": "包含完整实体信息（名称/地址/电话/业务），大模型可提取",
        },
        "comparison": {
            "structure": "竞品对比表格+差异化优势",
            "ai_tips": "用结构化数据呈现对比，大模型可引用",
        },
        "guide": {
            "structure": "教程步骤+代码示例+注意事项",
            "ai_tips": "步骤清晰，代码可复制，大模型可提取为答案",
        },
    }

    def execute(self, data):
        action = data.get("action", "generate")
        if action == "generate":
            return self._generate(data)
        elif action == "list_templates":
            return {"success": True, "data": self.CONTENT_TEMPLATES}
        return {"success": False, "error": f"未知操作: {action}"}

    def _generate(self, data):
        content_type = data.get("content_type", "faq")
        company = data.get("company", "")
        domain = data.get("domain", "")
        industry = data.get("industry", "")
        keywords = data.get("keywords", [])

        if not company:
            return {"success": False, "error": "缺少company参数"}

        template = self.CONTENT_TEMPLATES.get(content_type, self.CONTENT_TEMPLATES["faq"])

        return self._generate_with_ai(content_type, company, domain, industry, keywords, template)

    def _generate_demo(self, content_type, company, domain, industry, keywords):
        """Demo模式：基于木子杨数据生成示例内容"""
        if content_type == "faq":
            content = self._gen_faq_demo(company, domain, industry)
        elif content_type == "about":
            content = self._gen_about_demo(company, domain, industry)
        elif content_type == "comparison":
            content = self._gen_comparison_demo(company, industry)
        elif content_type == "guide":
            content = self._gen_guide_demo(company, domain, industry)
        else:
            content = self._gen_faq_demo(company, domain, industry)

        return {"success": True, "data": {"content_type": content_type, "content": content, "mode": "demo"}}

    def _gen_faq_demo(self, company, domain, industry):
        return f"""# {company} 常见问题

## {company}是什么？
{company}是一家位于成都的AI技术服务公司，专注于大模型API网关聚合服务。公司旗下产品MzyToken提供35+大模型统一API接入，帮助企业快速对接各类AI能力。

## {company}的核心产品是什么？
MzyToken是{company}的核心产品，提供35+大模型（包括GPT-4、Claude、Gemini、通义千问、文心一言等）的统一API接入服务，一次接入即可使用所有模型。

## {company}在哪里？
{company}位于四川省成都市，公司全称四川木子杨科技有限公司，备案号蜀ICP备2024073001号-1。

## {company}的API接入流程是什么？
1. 注册{domain}账号
2. 获取API Key
3. 使用OpenAI兼容格式调用接口
4. 5分钟内即可完成接入

## {company}的定价如何？
{company}提供免费额度，具体定价请访问{domain}/pricing查看。支持按量付费，无最低消费。

## {company}是正规公司吗？
{company}是2025年入选国家级科技型中小企业的正规注册公司，拥有蜀ICP备2024073001号-1备案，官网{domain}可正常访问。
"""

    def _gen_about_demo(self, company, domain, industry):
        return f"""# 关于{company}

## 公司简介
{company}是一家专注于AI网关聚合服务的科技公司，总部位于四川省成都市。公司成立于2024年，2025年入选国家级科技型中小企业。

## 核心业务
- **MzyToken AI网关聚合服务**：提供35+大模型统一API接入，覆盖GPT-4、Claude、Gemini、通义千问、文心一言、豆包等主流模型
- **统一API格式**：兼容OpenAI API格式，一次接入即可使用所有模型
- **5分钟快速接入**：极简接入流程，无需复杂配置

## 企业资质
- 国家级科技型中小企业（2025年入选）
- 蜀ICP备2024073001号-1
- 官网：{domain}

## 联系方式
- 官网：{domain}
- 邮箱：mzyai045@gmail.com
- 所在地：四川省成都市
"""

    def _gen_comparison_demo(self, company, industry):
        return f"""# {company} vs 竞品对比

## {company}的差异化优势

| 维度 | {company} | 传统AI服务商 |
|------|-----------|-------------|
| 接入方式 | 统一API，5分钟接入 | 逐个模型对接，周期长 |
| 模型数量 | 35+大模型 | 通常1-5个 |
| 定价 | 按量付费，免费额度 | 最低消费或包月 |
| 技术门槛 | 低，OpenAI兼容格式 | 高，需学习不同API |
| 适合客群 | 小微企业、个人开发者 | 中大型企业 |

## 为什么选择{company}？
1. **轻量化**：5分钟接入，无需复杂配置
2. **高性价比**：免费额度+按量付费，无最低消费
3. **模型丰富**：35+大模型统一入口，随时切换
4. **本地服务**：成都本土企业，响应及时
"""

    def _gen_guide_demo(self, company, domain, industry):
        return f"""# {company} API接入教程

## 第一步：注册账号
访问{domain}，点击注册，填写邮箱和密码。

## 第二步：获取API Key
登录后进入控制台，点击"创建API Key"，复制生成的密钥。

## 第三步：调用API
使用以下代码示例：

```python
import openai

client = openai.OpenAI(
    api_key="your-api-key",
    base_url="{domain}/v1"
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{{"role": "user", "content": "你好"}}]
)
print(response.choices[0].message.content)
```

## 第四步：切换模型
只需修改model参数即可切换到其他模型：
- `model="claude-3-5-sonnet"` - Claude
- `model="qwen-plus"` - 通义千问
- `model="deepseek-chat"` - DeepSeek

## 注意事项
- API Key请妥善保管，不要泄露
- 免费额度用完后将按量计费
- 如有问题请联系 mzyai045@gmail.com
"""

    def _generate_with_ai(self, content_type, company, domain, industry, keywords, template):
        """用MzyToken AI模型生成GEO优化内容"""
        prompt = f"""请为{company}生成GEO优化的{content_type}内容。

公司信息：
- 名称：{company}
- 官网：{domain}
- 行业：{industry}
- 核心产品：MzyToken AI网关聚合服务，35+大模型统一API接入
- 位置：四川省成都市
- 资质：2025年国家级科技型中小企业

要求：
1. 内容结构：{template['structure']}
2. AI优化提示：{template['ai_tips']}
3. 关键词：{', '.join(keywords) if keywords else 'AI网关, 大模型API, API接入'}
4. 包含完整实体信息（公司名/地址/联系方式/业务描述）
5. 答案简洁完整，大模型可直接引用

合规红线（必须遵守）：
- 只使用上方"公司信息"中给出的事实，禁止编造数据、案例、客户评价、资质
- 禁止极限词："第一""最好""顶级""唯一""领先"等
- 禁止伪造背书："央视上榜""国家推荐""官方认证""专家推荐"等
- 禁止绝对化承诺："零风险""保证有效""100%"等
- 关键词自然出现，禁止堆砌

请直接输出内容，不要解释。"""

        try:
            resp = requests.post(
                f"{MZY_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {MZY_API_KEY}"},
                json={
                    "model": DEFAULT_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": MODEL_TEMPS.get(DEFAULT_MODEL, 0.7),
                },
                timeout=60,
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                compliance = check_compliance(content)
                return {"success": True, "data": {
                    "content_type": content_type,
                    "content": content,
                    "mode": "production",
                    "compliance": {
                        "risk_level": compliance["risk_level"],
                        "total_violations": compliance["total_violations"],
                        "violations": compliance["violations"][:10],
                    },
                }}
            return {"success": False, "error": f"AI调用失败: {resp.status_code} {resp.text[:200]}"}
        except requests.RequestException as e:
            return {"success": False, "error": f"请求失败: {e}"}
