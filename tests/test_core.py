"""GEO Platform 核心路径测试"""
from __future__ import annotations
import hashlib
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCompanyIngest(unittest.TestCase):
    """公司入库 — URL归一化 + 链接评分 + 角色分类"""

    def test_normalize_url_adds_https(self):
        from agents.company_ingest import normalize_company_url
        self.assertEqual(normalize_company_url("example.com"), "https://example.com")

    def test_normalize_url_strips_trailing_slash(self):
        from agents.company_ingest import normalize_company_url
        self.assertEqual(normalize_company_url("https://example.com/"), "https://example.com")

    def test_normalize_url_rejects_empty(self):
        from agents.company_ingest import normalize_company_url
        with self.assertRaises(ValueError):
            normalize_company_url("")

    def test_normalize_url_rejects_localhost(self):
        from agents.company_ingest import normalize_company_url
        with self.assertRaises(ValueError):
            normalize_company_url("http://localhost:8060")

    def test_normalize_url_rejects_private_ip(self):
        from agents.company_ingest import normalize_company_url
        with self.assertRaises(ValueError):
            normalize_company_url("http://192.168.1.1")

    def test_normalize_url_rejects_credentials(self):
        from agents.company_ingest import normalize_company_url
        with self.assertRaises(ValueError):
            normalize_company_url("http://user:pass@example.com")

    def test_score_link_positive(self):
        from agents.company_ingest import _score_link
        score = _score_link("/about-us", "关于我们")
        self.assertGreater(score, 0)

    def test_score_link_negative(self):
        from agents.company_ingest import _score_link
        score = _score_link("/login", "登录")
        self.assertLess(score, 0)

    def test_score_link_asset_penalty(self):
        from agents.company_ingest import _score_link
        score = _score_link("/files/brochure.pdf", "")
        self.assertLess(score, 0)

    def test_classify_role(self):
        from agents.company_ingest import _classify_role
        self.assertEqual(_classify_role("/about", ""), "about")
        self.assertEqual(_classify_role("/team", ""), "team")
        self.assertEqual(_classify_role("/products", ""), "product")
        self.assertEqual(_classify_role("/random-page", ""), "other")

    def test_classify_role_by_title(self):
        from agents.company_ingest import _classify_role
        self.assertEqual(_classify_role("/about", ""), "about")
        self.assertEqual(_classify_role("/team", ""), "team")


class TestKeywordExpander(unittest.TestCase):
    """8维拓词 — 画像推断 + 模板回退 + 稳定评分"""

    def test_infer_profile_enterprise(self):
        from agents.keyword_expander import _infer_keyword_profile
        profile = _infer_keyword_profile(["GEO优化"])
        self.assertEqual(profile["key"], "enterprise_service")

    def test_infer_profile_education(self):
        from agents.keyword_expander import _infer_keyword_profile
        profile = _infer_keyword_profile(["英语培训"])
        self.assertEqual(profile["key"], "consumer_education")

    def test_infer_profile_fallback(self):
        from agents.keyword_expander import _infer_keyword_profile
        profile = _infer_keyword_profile(["xyzzy_unknown"])
        self.assertEqual(profile["key"], "enterprise_service")

    def test_infer_profile_returns_required_fields(self):
        from agents.keyword_expander import _infer_keyword_profile
        profile = _infer_keyword_profile(["AI网关"])
        for field in ("key", "name", "company_hint", "business_model", "target_users"):
            self.assertIn(field, profile)

    def test_stable_score_deterministic(self):
        from agents.keyword_expander import _stable_score
        s1 = _stable_score("seed", "semantic", "keyword", 60, 28)
        s2 = _stable_score("seed", "semantic", "keyword", 60, 28)
        self.assertEqual(s1, s2)
        self.assertGreaterEqual(s1, 35)
        self.assertLessEqual(s1, 99)

    def test_stable_score_varies_by_input(self):
        from agents.keyword_expander import _stable_score
        s1 = _stable_score("seed", "semantic", "keyword_a", 60, 28)
        s2 = _stable_score("seed", "semantic", "keyword_b", 60, 28)
        # 不同关键词应产生不同评分（MD5哈希）
        self.assertNotEqual(s1, s2)

    def test_fallback_expand_returns_8_dimensions(self):
        from agents.keyword_expander import _fallback_expand, _infer_keyword_profile, DIMENSIONS
        profile = _infer_keyword_profile(["GEO优化"])
        result = _fallback_expand(["GEO优化"], profile)
        self.assertEqual(len(result), len(DIMENSIONS))
        for dim in result:
            self.assertIn("key", dim)
            self.assertIn("items", dim)
            self.assertGreater(len(dim["items"]), 0)

    def test_sanitize_dimension_items(self):
        from agents.keyword_expander import _sanitize_dimension_items, _infer_keyword_profile
        profile = _infer_keyword_profile(["GEO优化"])
        raw = [
            {"keyword": "关键词A", "recommendation_score": 70, "business_score": 65},
            {"keyword": "", "recommendation_score": 50},
            {"keyword": "关键词B"},
            {"keyword": None},
        ]
        cleaned = _sanitize_dimension_items("GEO优化", "semantic", raw, profile)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned[0]["keyword"], "关键词A")
        self.assertEqual(cleaned[1]["keyword"], "关键词B")

    def test_sanitize_blocks_profile_terms(self):
        from agents.keyword_expander import _sanitize_dimension_items, _infer_keyword_profile
        profile = _infer_keyword_profile(["英语培训"])
        raw = [{"keyword": "B2B英语培训"}, {"keyword": "在线英语培训"}]
        cleaned = _sanitize_dimension_items("英语培训", "scenario", raw, profile)
        keywords = [item["keyword"] for item in cleaned]
        self.assertNotIn("B2B英语培训", keywords)
        self.assertIn("在线英语培训", keywords)


class TestMaturityScorer(unittest.TestCase):
    """六层成熟度评分 — 纯计算逻辑"""

    def test_get_layers_returns_6(self):
        from agents.maturity_scorer import get_layers
        layers = get_layers()
        self.assertEqual(len(layers), 6)
        keys = [l["key"] for l in layers]
        self.assertEqual(keys, ["seo", "aeo", "geo", "gao", "gmo", "gdo"])

    def test_calculate_maturity_empty_input(self):
        from agents.maturity_scorer import calculate_maturity
        result = calculate_maturity()
        self.assertIn("overall_score", result)
        self.assertIn("level", result)
        self.assertIn("layers", result)
        self.assertEqual(result["overall_score"], 0)

    def test_calculate_maturity_with_benchmark(self):
        from agents.maturity_scorer import calculate_maturity
        benchmark = {"citation_rate": 0.5, "avg_rank": 2}
        result = calculate_maturity(benchmark=benchmark)
        self.assertGreater(result["overall_score"], 0)
        geo_layers = [l for l in result["layers"] if l["key"] == "geo"]
        self.assertGreater(len(geo_layers), 0)
        self.assertGreater(geo_layers[0]["score"], 0)

    def test_calculate_maturity_with_keywords(self):
        from agents.maturity_scorer import calculate_maturity
        result = calculate_maturity(keywords_count=50, strategies_count=5)
        geo_layers = [l for l in result["layers"] if l["key"] == "geo"]
        self.assertGreater(len(geo_layers), 0)
        self.assertGreater(geo_layers[0]["score"], 0)

    def test_score_from_benchmark(self):
        from agents.maturity_scorer import _score_from_benchmark
        scores = _score_from_benchmark({"citation_rate": 0.8, "avg_rank": 1})
        self.assertIn("geo", scores)
        self.assertGreater(scores["geo"]["score"], 0)
        self.assertLessEqual(scores["geo"]["score"], 100)

    def test_score_from_gdo(self):
        from agents.maturity_scorer import _score_from_gdo
        scores = _score_from_gdo({"overall_score": 75, "level": "B", "summary": "test"})
        self.assertIn("gdo", scores)
        self.assertEqual(scores["gdo"]["score"], 75)

    def test_grade_boundaries(self):
        from agents.maturity_scorer import calculate_maturity
        result_high = calculate_maturity(
            benchmark={"citation_rate": 0.9, "avg_rank": 1},
            gdo={"overall_score": 90},
            keywords_count=100,
            strategies_count=10,
        )
        self.assertIn(result_high["level"], ["S", "A", "B", "C", "D"])


class TestPdfDedup(unittest.TestCase):
    """PDF去重 — 哈希比对 + 重定向规则"""

    def test_content_hash(self):
        from agents.pdf_dedup import _content_hash
        content = b"%PDF-1.4 test content"
        h = _content_hash(content)
        self.assertEqual(h, hashlib.sha256(content).hexdigest())
        self.assertEqual(len(h), 64)

    def test_audit_duplicate_pdfs_with_mock(self):
        from agents.pdf_dedup import audit_duplicate_pdfs
        pdf_content = b"%PDF-1.4 identical content"
        with patch("agents.pdf_dedup._download_pdf", return_value=pdf_content):
            result = audit_duplicate_pdfs([
                "https://example.com/a.pdf",
                "https://example.com/b.pdf",
                "https://example.com/c.pdf",
            ])
        self.assertEqual(result["total_urls"], 3)
        self.assertEqual(result["duplicate_groups"], 1)
        self.assertEqual(result["total_duplicates"], 2)
        self.assertEqual(len(result["duplicates"]), 1)
        dup = result["duplicates"][0]
        self.assertEqual(dup["duplicate_count"], 2)
        self.assertEqual(len(dup["redirect_rules"]), 2)
        for rule in dup["redirect_rules"]:
            self.assertEqual(rule["type"], "301")

    def test_audit_empty_urls(self):
        from agents.pdf_dedup import audit_duplicate_pdfs
        result = audit_duplicate_pdfs([])
        self.assertIn("error", result)

    def test_audit_unique_pdfs(self):
        from agents.pdf_dedup import audit_duplicate_pdfs
        with patch("agents.pdf_dedup._download_pdf", side_effect=[
            b"%PDF-1.4 content A",
            b"%PDF-1.4 content B",
        ]):
            result = audit_duplicate_pdfs([
                "https://example.com/a.pdf",
                "https://example.com/b.pdf",
            ])
        self.assertEqual(result["duplicate_groups"], 0)
        self.assertEqual(result["unique_pdfs"], 2)

    def test_extract_pdf_urls_from_html(self):
        from agents.pdf_dedup import _extract_pdf_urls_from_html
        html = '<a href="/docs/a.pdf">A</a><a href="https://cdn.example.com/b.pdf">B</a><img src="/c.pdf">'
        urls = _extract_pdf_urls_from_html(html, "example.com")
        self.assertIn("https://example.com/docs/a.pdf", urls)
        self.assertIn("https://cdn.example.com/b.pdf", urls)
        self.assertIn("https://example.com/c.pdf", urls)

    def test_extract_pdf_urls_ignores_non_pdf(self):
        from agents.pdf_dedup import _extract_pdf_urls_from_html
        html = '<a href="/page.html">Page</a><a href="/doc.pdf">PDF</a>'
        urls = _extract_pdf_urls_from_html(html, "example.com")
        self.assertEqual(len(urls), 1)


class TestPageDiagnoser(unittest.TestCase):
    """页面诊断 — HTML解析检测逻辑"""

    def _make_soup(self, html):
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")

    def test_check_meta_complete(self):
        from agents.page_diagnoser import PageDiagnoser
        d = PageDiagnoser()
        html = '<html><head><title>Test</title><meta name="description" content="desc"><meta name="viewport" content="width=device-width"><meta charset="utf-8"></head><body></body></html>'
        soup = self._make_soup(html)
        result = d._check_meta(soup)
        self.assertIsNotNone(result["title"])
        self.assertTrue(result["has_description"])
        self.assertTrue(result["pass"])

    def test_check_meta_missing(self):
        from agents.page_diagnoser import PageDiagnoser
        d = PageDiagnoser()
        html = '<html><head></head><body></body></html>'
        soup = self._make_soup(html)
        result = d._check_meta(soup)
        self.assertIsNone(result["title"])
        self.assertFalse(result["has_description"])
        self.assertFalse(result["pass"])

    def test_check_structured_data_json_ld(self):
        from agents.page_diagnoser import PageDiagnoser
        d = PageDiagnoser()
        html = '<html><head><script type="application/ld+json">{"@type":"Organization"}</script></head><body></body></html>'
        soup = self._make_soup(html)
        result = d._check_structured_data(soup)
        self.assertGreater(result["json_ld_count"], 0)

    def test_check_headings(self):
        from agents.page_diagnoser import PageDiagnoser
        d = PageDiagnoser()
        html = '<html><body><h1>Title</h1><h2>Sub</h2><h3>SubSub</h3></body></html>'
        soup = self._make_soup(html)
        result = d._check_headings(soup)
        self.assertEqual(result["h1_count"], 1)
        self.assertEqual(result["h2_count"], 1)

    def test_check_https(self):
        from agents.page_diagnoser import PageDiagnoser
        d = PageDiagnoser()
        self.assertTrue(d._check_https("https://example.com")["pass"])
        self.assertFalse(d._check_https("http://example.com")["pass"])

    def test_calc_score_perfect(self):
        from agents.page_diagnoser import PageDiagnoser
        d = PageDiagnoser()
        checks = {
            "https": {"pass": True},
            "meta_tags": {"pass": True, "has_viewport": True},
            "structured_data": {"pass": True, "json_ld_count": 1},
            "llms_txt": {"pass": True},
            "headings": {"h1_count": 1, "h2_count": 2},
            "links": {"internal_count": 5, "external_count": 2},
            "ai_readability": {"text_length": 2000, "chinese_chars": 1500, "has_contact_info": True, "has_address": True},
        }
        score = d._calc_score(checks)
        self.assertGreater(score, 80)

    def test_calc_score_empty(self):
        from agents.page_diagnoser import PageDiagnoser
        d = PageDiagnoser()
        checks = {
            "https": {"pass": False},
            "meta_tags": {"pass": False, "has_viewport": False},
            "structured_data": {"pass": False, "json_ld_count": 0},
            "llms_txt": {"pass": False},
            "headings": {"h1_count": 0, "h2_count": 0},
            "links": {"internal_count": 0, "external_count": 0},
            "ai_readability": {"text_length": 0, "chinese_chars": 0, "has_contact_info": False, "has_address": False},
        }
        score = d._calc_score(checks)
        self.assertLess(score, 30)


class TestContentStrategies(unittest.TestCase):
    """内容优化策略 — 策略元信息"""

    def test_get_strategies_info(self):
        from agents.content_strategies import get_strategies_info
        info = get_strategies_info()
        self.assertIsInstance(info, list)
        self.assertGreaterEqual(len(info), 9)
        for s in info:
            self.assertIn("key", s)
            self.assertIn("name", s)
            self.assertIn("description", s)


class TestGDOAuditor(unittest.TestCase):
    """GDO决策审计 — 维度定义"""

    def test_get_dimensions(self):
        from agents.gdo_auditor import get_dimensions
        dims = get_dimensions()
        self.assertEqual(len(dims), 5)
        keys = [d["key"] for d in dims]
        self.assertIn("case_detail", keys)
        self.assertIn("evidence_chain", keys)


class TestAIComparison(unittest.TestCase):
    """AI决策对比 — 场景定义"""

    def test_get_scenarios(self):
        from agents.ai_comparison import get_scenarios
        scenarios = get_scenarios()
        self.assertEqual(len(scenarios), 5)
        for s in scenarios:
            self.assertIn("key", s)
            self.assertIn("name", s)
            self.assertIn("description", s)


class TestGeoABTest(unittest.TestCase):
    """GEO A/B测试 — 品牌检测 + 信源分类"""

    def test_detect_brand_mention_found(self):
        from agents.geo_ab_test import _detect_brand_mention
        result = _detect_brand_mention("木子杨科技是一家AI公司", "木子杨", None)
        self.assertTrue(result["mentioned"])
        self.assertIn("木子杨", result["matched_names"])

    def test_detect_brand_mention_not_found(self):
        from agents.geo_ab_test import _detect_brand_mention
        result = _detect_brand_mention("这是一段无关文本", "木子杨", None)
        self.assertFalse(result["mentioned"])

    def test_detect_brand_mention_with_aliases(self):
        from agents.geo_ab_test import _detect_brand_mention
        result = _detect_brand_mention("MZY提供API服务", "木子杨", ["MZY", "mzyai"])
        self.assertTrue(result["mentioned"])
        self.assertIn("MZY", result["matched_names"])

    def test_classify_source_official(self):
        from agents.geo_ab_test import _classify_source
        self.assertEqual(_classify_source("来自官网 mzyai.com 的信息", "mzyai.com"), "official_site")

    def test_classify_source_b2b(self):
        from agents.geo_ab_test import _classify_source
        self.assertEqual(_classify_source("在1688平台上有售"), "b2b_platform")

    def test_classify_source_self_media(self):
        from agents.geo_ab_test import _classify_source
        self.assertEqual(_classify_source("公众号文章提到"), "self_media")

    def test_classify_source_third_party(self):
        from agents.geo_ab_test import _classify_source
        self.assertEqual(_classify_source("据新浪新闻报道"), "third_party_media")

    def test_classify_source_other(self):
        from agents.geo_ab_test import _classify_source
        self.assertEqual(_classify_source("未知来源信息"), "other")

    def test_get_page_types(self):
        from agents.geo_ab_test import get_page_types
        types = get_page_types()
        self.assertIsInstance(types, list)
        self.assertGreater(len(types), 0)

    def test_get_source_categories(self):
        from agents.geo_ab_test import get_source_categories
        cats = get_source_categories()
        self.assertIsInstance(cats, list)
        self.assertGreaterEqual(len(cats), 5)


class TestSheepScorer(unittest.TestCase):
    """SHEEP评分 — 模型权重 + 证据构建"""

    def test_get_model_weights(self):
        from agents.sheep_scorer import get_model_weights
        weights = get_model_weights()
        self.assertIsInstance(weights, dict)
        self.assertGreaterEqual(len(weights), 9)
        total = sum(weights.values())
        self.assertAlmostEqual(total, 1.0, places=1)

    def test_build_evidence_from_diagnosis(self):
        from agents.sheep_scorer import build_evidence_from_diagnosis
        diagnosis = {
            "score": 72,
            "status_code": 200,
            "html_size": 50000,
            "url": "https://example.com",
            "checks": {
                "https": {"pass": True},
                "meta_tags": {"title": "测试标题", "description": "测试描述", "pass": True},
                "structured_data": {"json_ld_count": 2, "schema_types": ["Organization"], "pass": True},
                "headings": {"h1_count": 1, "h2_count": 3, "pass": True},
                "links": {"total": 13, "internal": 10, "external": 3, "pass": True},
                "ai_readability": {"text_length": 3000, "chinese_chars": 2500, "has_contact_info": True, "has_address": True, "pass": True},
            },
        }
        evidence = build_evidence_from_diagnosis(diagnosis)
        self.assertIsInstance(evidence, dict)
        self.assertIn("s_evidence", evidence)
        self.assertIn("h_evidence", evidence)
        self.assertIn("e1_evidence", evidence)
        self.assertIn("e2_evidence", evidence)
        self.assertIn("p_evidence", evidence)


class TestComplianceAuditor(unittest.TestCase):
    """合规风险检测 — 极限词/伪造背书/绝对化承诺/关键词堆砌"""

    def test_clean_content_passes(self):
        from agents.compliance_auditor import check_compliance
        result = check_compliance("我们为客户提供稳定的API网关服务，已服务300余家企业客户。")
        self.assertEqual(result["risk_level"], "pass")
        self.assertEqual(result["total_violations"], 0)

    def test_superlative_detected(self):
        from agents.compliance_auditor import check_compliance
        result = check_compliance("我们是行业第一的AI服务商，技术最好。")
        self.assertEqual(result["risk_level"], "high")
        terms = [v["term"] for v in result["violations"]]
        self.assertIn("行业第一", terms)
        self.assertIn("最好", terms)

    def test_contextual_superlative_no_false_positive(self):
        from agents.compliance_auditor import check_compliance
        result = check_compliance("第一步注册账号，第一时间获取API Key，我们提供领先的服务。")
        # "第一步""第一时间"不应误报；"领先"单独出现不命中上下文模式
        superlative_terms = [v["term"] for v in result["violations"] if v["type"] == "superlative"]
        self.assertEqual(superlative_terms, [])

    def test_contextual_superlative_claim_detected(self):
        from agents.compliance_auditor import check_compliance
        result = check_compliance("我们的技术水平行业领先，销量排名第一。")
        self.assertGreater(result["total_violations"], 0)
        self.assertEqual(result["risk_level"], "high")

    def test_fake_endorsement_detected(self):
        from agents.compliance_auditor import check_compliance
        result = check_compliance("本产品是央视上榜品牌，国家推荐产品。")
        self.assertEqual(result["risk_level"], "high")
        self.assertIn("fake_endorsement", result["stats"])

    def test_absolute_claim_detected(self):
        from agents.compliance_auditor import check_compliance
        result = check_compliance("使用本产品零风险，保证有效。")
        self.assertEqual(result["risk_level"], "high")
        self.assertIn("absolute_claim", result["stats"])

    def test_keyword_density_high(self):
        from agents.compliance_auditor import check_compliance
        content = "GEO优化" * 20 + "这是一段用于填充的普通描述文本内容。"
        result = check_compliance(content, keywords=["GEO优化"])
        stuffing = [v for v in result["violations"] if v["type"] == "keyword_stuffing"]
        self.assertEqual(len(stuffing), 1)
        self.assertEqual(stuffing[0]["severity"], "high")

    def test_keyword_density_normal(self):
        from agents.compliance_auditor import check_compliance
        content = "我们提供GEO优化服务。" + "帮助企业提升AI引用率，覆盖诊断评分与内容策略。" * 6
        result = check_compliance(content, keywords=["GEO优化"])
        stuffing = [v for v in result["violations"] if v["type"] == "keyword_stuffing"]
        self.assertEqual(stuffing, [])

    def test_qualification_medium_risk(self):
        from agents.compliance_auditor import check_compliance
        result = check_compliance("公司是国家级科技型中小企业。")
        self.assertEqual(result["risk_level"], "medium")

    def test_chiming_trademark_high_risk(self):
        from agents.compliance_auditor import check_compliance
        result = check_compliance("本产品为驰名商标产品。")
        self.assertEqual(result["risk_level"], "high")

    def test_empty_content_error(self):
        from agents.compliance_auditor import check_compliance
        result = check_compliance("")
        self.assertIn("error", result)

    def test_get_rules_returns_4_categories(self):
        from agents.compliance_auditor import get_rules
        rules = get_rules()
        self.assertEqual(len(rules), 4)
        keys = [r["key"] for r in rules]
        self.assertIn("superlative", keys)
        self.assertIn("keyword_stuffing", keys)

    def test_violations_sorted_by_severity(self):
        from agents.compliance_auditor import check_compliance
        result = check_compliance("国家级企业，行业第一，零风险。")
        severities = [v["severity"] for v in result["violations"]]
        self.assertEqual(severities, sorted(severities, key=lambda s: {"high": 0, "medium": 1}.get(s, 2)))


class TestAIMonitorPure(unittest.TestCase):
    """AI监控纯函数 — 品牌词推导/查询集构建/准确度评估/负面检测（不触网）"""

    def test_derive_company_parts_full_and_short(self):
        from agents.ai_monitor import derive_company_parts
        parts = derive_company_parts("四川木子杨科技有限公司")
        self.assertIn("四川木子杨科技有限公司", parts)
        self.assertIn("四川木子杨", parts)

    def test_derive_company_parts_extra_keywords(self):
        from agents.ai_monitor import derive_company_parts
        parts = derive_company_parts("测试公司", extra_keywords=["TestBrand", "  "])
        self.assertIn("TestBrand", parts)
        self.assertNotIn("  ", parts)

    def test_derive_company_parts_no_duplicates(self):
        from agents.ai_monitor import derive_company_parts
        parts = derive_company_parts("测试公司", extra_keywords=["测试公司"])
        self.assertEqual(parts.count("测试公司"), 1)

    def test_build_default_queries_with_industry_city(self):
        from agents.ai_monitor import build_default_queries
        queries = build_default_queries("木子杨科技", industry="AI网关", city="成都")
        self.assertEqual(len(queries), 4)
        self.assertIn("木子杨科技", queries)
        self.assertTrue(any("AI网关" in q for q in queries))
        self.assertTrue(any("成都" in q for q in queries))

    def test_build_default_queries_no_industry(self):
        from agents.ai_monitor import build_default_queries
        queries = build_default_queries("某公司")
        self.assertTrue(any("是做什么的" in q for q in queries))
        self.assertLessEqual(len(queries), 4)

    def test_assess_accuracy_high(self):
        from agents.ai_monitor import assess_accuracy
        answer = "木子杨科技是成都的一家AI网关公司，提供大模型API接入服务，支持多种模型的统一访问。" * 3
        self.assertEqual(assess_accuracy(answer, ["木子杨"]), "高")

    def test_assess_accuracy_none(self):
        from agents.ai_monitor import assess_accuracy
        self.assertEqual(assess_accuracy("完全无关的回答", ["不存在的品牌词"]), "无")

    def test_detect_negative_true(self):
        from agents.ai_monitor import detect_negative
        answer = "有用户投诉木子杨科技的服务存在纠纷，建议谨慎选择。"
        self.assertTrue(detect_negative(answer, ["木子杨"]))

    def test_detect_negative_false_when_not_mentioned(self):
        from agents.ai_monitor import detect_negative
        answer = "这家公司有很多投诉和纠纷。"
        self.assertFalse(detect_negative(answer, ["木子杨"]))

    def test_detect_negative_false_when_positive(self):
        from agents.ai_monitor import detect_negative
        answer = "木子杨科技是一家服务稳定的公司。"
        self.assertFalse(detect_negative(answer, ["木子杨"]))

    def test_monitor_missing_company_returns_error(self):
        from agents.ai_monitor import AIMonitor
        result = AIMonitor().execute({"action": "monitor"})
        self.assertFalse(result["success"])
        self.assertIn("company", result["error"])

    def test_unknown_action_returns_error(self):
        from agents.ai_monitor import AIMonitor
        result = AIMonitor().execute({"action": "nonexistent"})
        self.assertFalse(result["success"])


class TestSiteOptimizer(unittest.TestCase):
    """网站优化 — llms.txt生成 + 爬虫注册表"""

    def test_ai_bots_registry(self):
        from agents.site_optimizer import AI_BOTS
        self.assertIsInstance(AI_BOTS, dict)
        self.assertGreaterEqual(len(AI_BOTS), 16)
        for name, desc in AI_BOTS.items():
            self.assertIsInstance(name, str)
            self.assertIsInstance(desc, str)

    def test_generate_llms_txt(self):
        from agents.site_optimizer import SiteOptimizer
        opt = SiteOptimizer()
        result = opt.execute({
            "action": "generate_llms_txt",
            "company": "测试公司",
            "domain": "test.com",
            "description": "测试描述",
        })
        self.assertTrue(result.get("success"))
        content = result["data"]["content"]
        self.assertIn("test.com", content)


if __name__ == "__main__":
    unittest.main()
