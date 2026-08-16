"""页面诊断Agent - 基于真实网页抓取+GEO分析报告数据"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json
import re
import os


class PageDiagnoser:
    name = "PageDiagnoser"
    description = "页面GEO诊断：技术SEO检测、结构化数据检查、AI可读性评估"

    # SPA特征：body可见文本极少 + 存在大型JS bundle
    SPA_TEXT_THRESHOLD = 50
    SPA_JS_SIZE_HINT = 50000

    def execute(self, data):
        url = data.get("url", "")
        source_dir = data.get("source_dir", "")
        if not url and not source_dir:
            return {"success": False, "error": "缺少url或source_dir参数"}

        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url
        verify_ssl = bool(data.get("verify_ssl", True))

        results = {
            "url": url,
            "domain": urlparse(url).netloc if url else "",
            "checks": {},
            "issues": [],
            "score": 0,
        }

        # 优先用本地源码目录做深度分析
        if source_dir and os.path.isdir(source_dir):
            self._analyze_source_dir(results, source_dir)
            results["source_dir"] = source_dir

        # 线上抓取（即使有source_dir也跑，对比线上vs源码）
        if url:
            try:
                resp = requests.get(url, timeout=10, verify=verify_ssl, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; GEO-Bot/1.0)"
                })
                content_type = resp.headers.get("Content-Type", "")
                if "charset" not in content_type.lower():
                    resp.encoding = "utf-8"
                html = resp.text
                soup = BeautifulSoup(html, "html.parser")
                results["status_code"] = resp.status_code
                results["html_size"] = len(html)
                results["charset_declared"] = "charset" in content_type.lower()
            except requests.RequestException as e:
                results["fetch_error"] = str(e)
                results["score"] = 0
                return {"success": True, "data": results}

            # SPA检测
            is_spa = self._detect_spa(soup, html)
            results["is_spa"] = is_spa
            if is_spa:
                results["issues"].append({
                    "severity": "high", "category": "SPA渲染",
                    "message": "网站为SPA单页应用，HTML空壳无服务端渲染内容，AI爬虫无法提取页面文本/标题/结构化数据",
                    "fix": "方案1: 添加SSR/SSG预渲染（如vite-plugin-ssr）方案2: 部署prerender中间件方案3: 在index.html中注入静态meta/JSON-LD/llms.txt引用",
                })

            results["checks"]["https"] = self._check_https(url)
            results["checks"]["meta_tags"] = self._check_meta(soup)
            results["checks"]["structured_data"] = self._check_structured_data(soup)
            results["checks"]["llms_txt"] = self._check_llms_txt(url, verify_ssl)
            results["checks"]["headings"] = self._check_headings(soup)
            results["checks"]["links"] = self._check_links(soup, url)
            results["checks"]["ai_readability"] = self._check_ai_readability(soup)

            # 备案/信任信息提取（从HTML + 尝试常见路径）
            results["checks"]["trust_signals"] = self._check_trust_signals(soup, url, verify_ssl)

            results["issues"].extend(self._collect_issues(results["checks"]))
            if not results.get("charset_declared", False):
                results["issues"].append({
                    "severity": "medium", "category": "AI适配",
                    "message": "HTTP响应头未声明charset，部分AI爬虫可能按ISO-8859-1误解码中文内容",
                })
            results["score"] = self._calc_score(results["checks"])

        return {"success": True, "data": results}

    def _detect_spa(self, soup, html):
        """检测SPA：body可见文本极少 + 有大型JS bundle"""
        body = soup.find("body")
        if not body:
            return False
        for tag in body(["script", "style"]):
            tag.decompose()
        visible_text = body.get_text(strip=True)
        if len(visible_text) < self.SPA_TEXT_THRESHOLD:
            scripts = soup.find_all("script", src=True)
            for s in scripts:
                src = s.get("src", "")
                # Vite/webpack chunk命名特征 或 内联大脚本
                if re.search(r'(index|app|main|chunk)-[A-Za-z0-9]{6,}\.js', src):
                    return True
            inline_scripts = soup.find_all("script", src=False)
            for s in inline_scripts:
                if s.string and len(s.string) > self.SPA_JS_SIZE_HINT:
                    return True
        return False

    def _check_trust_signals(self, soup, url, verify_ssl=True):
        """提取备案号/公安备案/营业执照等信任信号"""
        text = soup.get_text(separator=" ", strip=True)
        # 尝试从footer等常见位置提取
        footer = soup.find("footer")
        footer_text = footer.get_text(separator=" ", strip=True) if footer else ""

        icp = self._extract_icp(text + " " + footer_text)
        police = self._extract_police(text + " " + footer_text)
        license_no = self._extract_business_license(text + " " + footer_text)

        # 尝试从 /about /contact 等页面补充（SPA可能渲染后才可见）
        if not icp and url:
            parsed = urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            for path in ["/about", "/contact", "/footer"]:
                try:
                    r = requests.get(f"{base}{path}", timeout=5, verify=verify_ssl, headers={
                        "User-Agent": "Mozilla/5.0 (compatible; GEO-Bot/1.0)"
                    })
                    if r.status_code == 200:
                        extra = BeautifulSoup(r.text, "html.parser").get_text(separator=" ", strip=True)
                        if not icp:
                            icp = self._extract_icp(extra)
                        if not police:
                            police = self._extract_police(extra)
                        if not license_no:
                            license_no = self._extract_business_license(extra)
                except requests.RequestException:
                    pass

        has_any = bool(icp or police or license_no)
        return {
            "icp": icp,
            "police_record": police,
            "business_license": license_no,
            "pass": has_any,
            "detail": f"ICP:{icp or '无'} 公安:{police or '无'} 营业执照:{license_no or '无'}",
        }

    @staticmethod
    def _extract_icp(text):
        m = re.search(r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤川青藏琼宁]ICP[备证]?(\d{6,10}号?[-—]\d{1,3})?', text)
        if m:
            return m.group(0)
        m = re.search(r'ICP[备证]?[：:]?\s*(\d{6,10}[-—]?\d{0,3})', text)
        return m.group(0) if m else None

    @staticmethod
    def _extract_police(text):
        m = re.search(r'公网安备[：:]?\s*(\d{14})号?', text)
        if m:
            return f"公网安备{m.group(1)}号"
        m = re.search(r'(\d{14})号?$', text)
        return None

    @staticmethod
    def _extract_business_license(text):
        m = re.search(r'统一社会信用代码[：:]?\s*([0-9A-Z]{18})', text)
        return m.group(1) if m else None

    def _analyze_source_dir(self, results, source_dir):
        """分析本地源码目录结构，提取SPA框架/入口/路由等信息"""
        info = {"path": source_dir, "framework": None, "entry_html": None, "routes": [], "has_llms_txt": False}

        # 检测框架
        pkg_path = os.path.join(source_dir, "package.json")
        if os.path.isfile(pkg_path):
            try:
                pkg = json.load(open(pkg_path, encoding="utf-8"))
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "vue" in deps or "vite" in deps:
                    info["framework"] = "Vue+Vite"
                elif "react" in deps:
                    info["framework"] = "React"
                elif "svelte" in deps:
                    info["framework"] = "Svelte"
            except (json.JSONDecodeError, OSError):
                pass

        # 找入口HTML
        for candidate in ["index.html", "public/index.html", "dist/index.html", "static/index.html"]:
            full = os.path.join(source_dir, candidate)
            if os.path.isfile(full):
                info["entry_html"] = candidate
                # 从入口HTML提取已有meta/JSON-LD
                try:
                    html = open(full, encoding="utf-8").read()
                    soup = BeautifulSoup(html, "html.parser")
                    existing_meta = []
                    for m in soup.find_all("meta", attrs={"name": True}):
                        existing_meta.append(f'{m["name"]}={m.get("content", "")[:60]}')
                    info["existing_meta"] = existing_meta
                    json_ld = soup.find_all("script", type="application/ld+json")
                    info["existing_json_ld_count"] = len(json_ld)
                except OSError:
                    pass
                break

        # 检测路由文件
        for pattern in ["src/router/**", "src/routes/**", "src/App.vue", "src/main.ts"]:
            for root, dirs, files in os.walk(source_dir):
                for f in files:
                    if "router" in f.lower() or "route" in f.lower():
                        info["routes"].append(os.path.relpath(os.path.join(root, f), source_dir))
                break  # 只看第一层

        # 检测llms.txt
        for name in ["llms.txt", "public/llms.txt", "dist/llms.txt", "static/llms.txt"]:
            if os.path.isfile(os.path.join(source_dir, name)):
                info["has_llms_txt"] = True
                break

        results["source_analysis"] = info

    def _check_https(self, url):
        is_https = url.startswith("https://")
        return {"pass": is_https, "detail": "HTTPS" if is_https else "HTTP（不安全）"}

    def _check_meta(self, soup):
        title = soup.find("title")
        desc = soup.find("meta", attrs={"name": "description"})
        viewport = soup.find("meta", attrs={"name": "viewport"})
        charset = soup.find("meta", attrs={"charset": True})

        return {
            "title": title.string.strip()[:100] if title and title.string else None,
            "has_description": desc is not None,
            "description": desc.get("content", "")[:200] if desc else None,
            "has_viewport": viewport is not None,
            "has_charset": charset is not None,
            "pass": bool(title and title.string and desc),
        }

    def _check_structured_data(self, soup):
        json_ld = soup.find_all("script", type="application/ld+json")
        schemas = []
        for tag in json_ld:
            try:
                data = json.loads(tag.string)
                schemas.append(data.get("@type", "unknown"))
            except (json.JSONDecodeError, TypeError):
                pass

        microdata = soup.find_all(attrs={"itemscope": True})

        return {
            "json_ld_count": len(json_ld),
            "schema_types": schemas,
            "microdata_count": len(microdata),
            "pass": len(json_ld) > 0 or len(microdata) > 0,
            "detail": f"JSON-LD: {len(json_ld)}个, Microdata: {len(microdata)}个",
        }

    def _check_llms_txt(self, url, verify_ssl=True):
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        found = False
        try:
            resp = requests.get(f"{base}/llms.txt", timeout=5, verify=verify_ssl, headers={
                "User-Agent": "Mozilla/5.0 (compatible; GEO-Bot/1.0)"
            })
            found = resp.status_code == 200
        except requests.RequestException:
            pass

        ai_txt_found = False
        try:
            resp = requests.get(f"{base}/ai.txt", timeout=5, headers={
                "User-Agent": "Mozilla/5.0 (compatible; GEO-Bot/1.0)"
            })
            ai_txt_found = resp.status_code == 200
        except requests.RequestException:
            pass

        return {
            "llms_txt": found,
            "ai_txt": ai_txt_found,
            "pass": found,
            "detail": "已部署" if found else "未部署（大模型无法定向抓取）",
        }

    def _check_headings(self, soup):
        h1 = soup.find_all("h1")
        h2 = soup.find_all("h2")
        h3 = soup.find_all("h3")
        return {
            "h1_count": len(h1),
            "h1_text": [h.get_text(strip=True)[:80] for h in h1],
            "h2_count": len(h2),
            "h3_count": len(h3),
            "pass": len(h1) == 1,
            "detail": f"H1: {len(h1)}个, H2: {len(h2)}个, H3: {len(h3)}个",
        }

    def _check_links(self, soup, base_url):
        links = soup.find_all("a", href=True)
        internal = 0
        external = 0
        for a in links:
            href = a["href"]
            if href.startswith("/") or base_url in href:
                internal += 1
            elif href.startswith("http"):
                external += 1

        return {
            "total": len(links),
            "internal": internal,
            "external": external,
            "pass": len(links) > 5,
        }

    def _check_ai_readability(self, soup):
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        word_count = len(text.split())
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))

        has_contact = bool(re.search(r'(电话|联系|邮箱|@|微信|客服|400-|1[3-9]\d{9})', text))
        has_address = bool(re.search(r'(地址|路|街|号|区|市|省)', text))

        return {
            "text_length": len(text),
            "chinese_chars": chinese_chars,
            "word_count": word_count,
            "has_contact_info": has_contact,
            "has_address": has_address,
            "pass": chinese_chars > 200 and has_contact,
            "detail": f"中文字符{chinese_chars}个, 联系方式{'有' if has_contact else '无'}, 地址{'有' if has_address else '无'}",
        }

    def _collect_issues(self, checks):
        issues = []
        if not checks["https"]["pass"]:
            issues.append({"severity": "high", "category": "安全", "message": "未使用HTTPS"})
        if not checks["meta_tags"]["pass"]:
            issues.append({"severity": "high", "category": "元数据", "message": "缺少title或description"})
        if not checks["meta_tags"].get("has_viewport"):
            issues.append({"severity": "medium", "category": "移动端", "message": "缺少viewport meta标签"})
        if not checks["structured_data"]["pass"]:
            issues.append({"severity": "high", "category": "结构化数据", "message": "无JSON-LD或Microdata，大模型无法提取结构化信息"})
        if not checks["llms_txt"]["pass"]:
            issues.append({"severity": "high", "category": "AI适配", "message": "未部署llms.txt，大模型无法定向抓取"})
        if checks["headings"]["h1_count"] == 0:
            issues.append({"severity": "medium", "category": "语义结构", "message": "缺少H1标签"})
        elif checks["headings"]["h1_count"] > 1:
            issues.append({"severity": "low", "category": "语义结构", "message": f"有{checks['headings']['h1_count']}个H1标签，建议只保留1个"})
        if not checks["ai_readability"]["has_contact_info"]:
            issues.append({"severity": "high", "category": "信任要素", "message": "页面无联系方式信息"})
        if not checks["ai_readability"]["has_address"]:
            issues.append({"severity": "medium", "category": "信任要素", "message": "页面无地址信息"})
        if checks["ai_readability"]["chinese_chars"] < 100:
            issues.append({"severity": "medium", "category": "内容", "message": "页面文本内容过少，大模型可提取信息不足"})
        # 备案/信任信号
        trust = checks.get("trust_signals", {})
        if not trust.get("icp"):
            issues.append({"severity": "high", "category": "信任要素", "message": "未检测到ICP备案号，AI引擎和用户无法验证网站合法性"})
        if not trust.get("police_record"):
            issues.append({"severity": "medium", "category": "信任要素", "message": "未检测到公安备案号"})
        return issues

    def _calc_score(self, checks):
        score = 100
        if not checks["https"]["pass"]:
            score -= 15
        if not checks["meta_tags"]["pass"]:
            score -= 10
        if not checks["meta_tags"].get("has_viewport"):
            score -= 5
        if not checks["structured_data"]["pass"]:
            score -= 20
        if not checks["llms_txt"]["pass"]:
            score -= 15
        if checks["headings"]["h1_count"] == 0:
            score -= 5
        if not checks["ai_readability"]["has_contact_info"]:
            score -= 10
        if not checks["ai_readability"]["has_address"]:
            score -= 5
        if checks["ai_readability"]["chinese_chars"] < 100:
            score -= 10
        trust = checks.get("trust_signals", {})
        if not trust.get("icp"):
            score -= 10
        if not trust.get("police_record"):
            score -= 3
        return max(0, score)
