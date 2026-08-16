/**
 * GEO Platform — Pi agent 封装扩展
 *
 * 把 GEO 平台（Flask API）封装为 Pi agent 的原生能力：
 *   1. 注册 mzyai provider —— 复用 GEO 平台的 OpenAI 兼容网关（token.mzyai.com），
 *      Pi 的编排大脑直接走现有 MZY_API_KEY，无需额外密钥。
 *   2. 注册 GEO 工具集 —— 诊断 / SHEEP 评分 / 优化 / 案例查询，Pi 作为编排者
 *      自主决定调用顺序，把线性 Pipeline 升级为 Agent 循环。
 *
 * 依赖的 GEO Flask 服务通过 HTTP 调用（GEO_PLATFORM_URL，默认 http://localhost:8060）。
 *
 * 用法：
 *   pi -e ./pi-agent/geo-extension.ts --model mzyai/deepseek-v4-pro
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const GEO_BASE = process.env.GEO_PLATFORM_URL || "http://localhost:8060";
const GEO_TOKEN = process.env.GEO_API_TOKEN || "";

async function geoFetch(path: string, body?: unknown): Promise<any> {
	const headers: Record<string, string> = { "Content-Type": "application/json" };
	if (GEO_TOKEN) headers["Authorization"] = `Bearer ${GEO_TOKEN}`;

	const opts: RequestInit =
		body === undefined
			? { method: "GET", headers }
			: { method: "POST", headers, body: JSON.stringify(body) };

	const resp = await fetch(`${GEO_BASE}${path}`, opts);
	const text = await resp.text();
	let data: any;
	try {
		data = JSON.parse(text);
	} catch {
		data = { raw: text };
	}
	if (!resp.ok) {
		const msg = data?.error || data?.message || text.slice(0, 300);
		throw new Error(`GEO API ${resp.status} ${path}: ${msg}`);
	}
	return data;
}

function jsonResult(obj: unknown, details: Record<string, unknown> = {}) {
	return {
		content: [{ type: "text" as const, text: JSON.stringify(obj, null, 2) }],
		details,
	};
}

// 统一的工具包装：捕获异常，把错误作为可读文本返回给 LLM，让它能自我纠正
function wrap(fn: (params: any) => Promise<any>) {
	return async (_toolCallId: string, params: any) => {
		try {
			return await fn(params);
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			return {
				content: [{ type: "text" as const, text: `调用失败：${msg}` }],
				details: { error: msg },
				isError: true,
			};
		}
	};
}

export default function geoExtension(pi: ExtensionAPI) {
	// ------------------------------------------------------------------
	// Provider: mzyai 网关（OpenAI 兼容，复用 GEO 平台的 LLM 通道）
	// ------------------------------------------------------------------
	pi.registerProvider("mzyai", {
		name: "MZY AI Gateway",
		baseUrl: process.env.MZY_BASE_URL || "https://token.mzyai.com/v1",
		apiKey: "$MZY_API_KEY",
		api: "openai-completions",
		models: [
			{
				id: "deepseek-v4-pro",
				name: "DeepSeek V4 Pro",
				reasoning: false,
				input: ["text"],
				cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
				contextWindow: 65536,
				maxTokens: 8192,
				compat: { supportsDeveloperRole: false, maxTokensField: "max_tokens" },
			},
			{
				id: "glm-5.2",
				name: "GLM 5.2",
				reasoning: false,
				input: ["text"],
				cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
				contextWindow: 65536,
				maxTokens: 8192,
				compat: { supportsDeveloperRole: false, maxTokensField: "max_tokens" },
			},
			{
				id: "kimi-k3",
				name: "Kimi K3 (temperature 固定为 1)",
				reasoning: false,
				input: ["text"],
				cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
				contextWindow: 131072,
				maxTokens: 8192,
				compat: { supportsDeveloperRole: false, maxTokensField: "max_tokens" },
			},
		],
	});

	// ------------------------------------------------------------------
	// GEO 工具集
	// ------------------------------------------------------------------

	pi.registerTool({
		name: "geo_health",
		label: "GEO 健康检查",
		description: "检查 GEO 平台服务是否在线，返回服务状态、数据库与版本信息。任何 GEO 任务开始前先调用它确认平台可用。",
		parameters: Type.Object({}),
		execute: wrap(async () => {
			const data = await geoFetch("/health");
			return jsonResult(data, { status: data.status });
		}),
	});

	pi.registerTool({
		name: "geo_ingest",
		label: "GEO 企业入库",
		description: "抓取并入库一个企业官网，提取品牌词、产品、案例、联系信息，作为后续诊断与评分的数据基础。",
		parameters: Type.Object({
			url: Type.String({ description: "企业官网 URL，如 https://www.example.com" }),
			company_name: Type.Optional(Type.String({ description: "企业名称，缺省时自动从页面提取" })),
		}),
		execute: wrap(async (p) => {
			const body: any = { url: p.url };
			if (p.company_name) body.company_name = p.company_name;
			const data = await geoFetch("/api/company/ingest", body);
			return jsonResult(data, { company: data.company_name });
		}),
	});

	pi.registerTool({
		name: "geo_diagnose",
		label: "GEO 页面诊断",
		description: "对单个页面做 GEO 诊断，返回 0-100 总分、等级、问题清单（errors/warnings）与优化机会（opportunities）。",
		parameters: Type.Object({
			url: Type.String({ description: "要诊断的页面 URL" }),
			verify_ssl: Type.Optional(Type.Boolean({ description: "是否校验 SSL 证书，默认 true" })),
		}),
		execute: wrap(async (p) => {
			const body: any = { url: p.url };
			if (p.verify_ssl !== undefined) body.verify_ssl = p.verify_ssl;
			const data = await geoFetch("/api/diagnose", body);
			return jsonResult(data, { score: data.score, grade: data.grade });
		}),
	});

	pi.registerTool({
		name: "geo_sheep_score",
		label: "GEO SHEEP 评分",
		description:
			"计算企业 GEO 综合得分（GEM）。SHEEP 五维：S 语义结构化 / H 人机双读 / E1 AI 生态融合 / E2 AI 内容适配 / P 性能可访问。返回各维度分、加权 GEM 总分、等级、反思校验与证据锚定信息。auto_diagnose=true 时自动做客观诊断作为证据锚点。",
		parameters: Type.Object({
			company_name: Type.String({ description: "企业名称" }),
			url: Type.Optional(Type.String({ description: "企业官网 URL，提供后可做客观证据锚定" })),
			industry: Type.Optional(Type.String({ description: "行业，如 软件服务、零售、制造" })),
			auto_diagnose: Type.Optional(Type.Boolean({ description: "是否自动诊断作为证据锚点，默认 true" })),
			verify_ssl: Type.Optional(Type.Boolean({ description: "诊断时是否校验 SSL，默认 true" })),
		}),
		execute: wrap(async (p) => {
			const body: any = { company_name: p.company_name };
			if (p.url) body.url = p.url;
			if (p.industry) body.industry = p.industry;
			if (p.auto_diagnose !== undefined) body.auto_diagnose = p.auto_diagnose;
			if (p.verify_ssl !== undefined) body.verify_ssl = p.verify_ssl;
			const data = await geoFetch("/api/sheep-score", body);
			return jsonResult(data, { gem_score: data.gem_score, grade: data.grade });
		}),
	});

	pi.registerTool({
		name: "geo_optimize",
		label: "GEO 站点优化",
		description:
			"基于诊断结果生成 GEO 优化产物。action=generate_all 时生成 llms.txt / robots.txt / sitemap.xml / meta 标签 / FAQ 等。返回生成的文件内容与部署建议。",
		parameters: Type.Object({
			action: Type.String({ description: "优化动作，通常用 generate_all" }),
			url: Type.Optional(Type.String({ description: "企业官网 URL" })),
			company_name: Type.Optional(Type.String({ description: "企业名称" })),
			industry: Type.Optional(Type.String({ description: "行业" })),
			products: Type.Optional(Type.Array(Type.String(), { description: "产品/服务列表" })),
			cases: Type.Optional(Type.Array(Type.String(), { description: "客户案例列表" })),
			contact: Type.Optional(Type.String({ description: "联系方式" })),
		}),
		execute: wrap(async (p) => {
			const body: any = { action: p.action };
			for (const k of ["url", "company_name", "industry", "products", "cases", "contact"]) {
				if (p[k] !== undefined) body[k] = p[k];
			}
			const data = await geoFetch("/api/optimize", body);
			return jsonResult(data, { files: data.files ? Object.keys(data.files) : [] });
		}),
	});

	pi.registerTool({
		name: "geo_companies",
		label: "GEO 企业列表",
		description: "列出已入库的所有企业及其 GEM 得分、等级、行业、URL。用于查看历史案例与对比。",
		parameters: Type.Object({}),
		execute: wrap(async () => {
			const data = await geoFetch("/api/companies");
			return jsonResult(data, { count: data.total });
		}),
	});

	pi.registerTool({
		name: "geo_cases",
		label: "GEO 案例前后对比",
		description: "返回所有优化案例的前后对比（诊断分、GEM 分、SHEEP 各维度变化），用于评估优化成效与复盘。",
		parameters: Type.Object({}),
		execute: wrap(async () => {
			const data = await geoFetch("/api/cases");
			return jsonResult(data, { count: data.total });
		}),
	});

	pi.registerTool({
		name: "geo_compliance_check",
		label: "GEO 内容合规检测",
		description:
			"检测内容的合规风险：极限词、伪造权威背书、绝对化承诺、关键词堆砌。2026-07 AI 内容监管新规下，违规内容会被 AI 引擎过滤并连累品牌可信度。任何要发布的内容交付前必须先过此检测，risk_level=high 时禁止交付。",
		parameters: Type.Object({
			content: Type.String({ description: "待检测的文本内容" }),
			keywords: Type.Optional(Type.Array(Type.String(), { description: "需检测密度的关键词，如品牌词/产品词" })),
		}),
		execute: wrap(async (p) => {
			const body: any = { content: p.content };
			if (p.keywords) body.keywords = p.keywords;
			const resp = await geoFetch("/api/compliance/check", body);
			const data = resp.data || resp;
			return jsonResult(data, { risk_level: data.risk_level, total_violations: data.total_violations });
		}),
	});
}
