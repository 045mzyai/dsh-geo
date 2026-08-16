"""公司官网入库服务 — 蒸馏自GEORank company_ingest.py

URL归一化 + 公网地址校验 + 候选链接提取 + 页面角色分类
"""
from __future__ import annotations
import ipaddress
import re
import socket
from typing import Iterable, Optional
from urllib.parse import urlparse, urlunparse
import requests

_ASSET_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico", ".pdf", ".zip", ".xml", ".json", ".txt", ".css", ".js")

_POSITIVE_KEYWORDS = {
    "about": 90, "about-us": 90, "company": 84, "team": 80, "leadership": 72,
    "founders": 68, "story": 64, "mission": 60, "platform": 58, "product": 56,
    "products": 56, "solution": 52, "solutions": 52, "technology": 48, "ai": 44, "overview": 42,
}

_NEGATIVE_KEYWORDS = {
    "login": -120, "signin": -120, "sign-in": -120, "signup": -120, "sign-up": -120,
    "register": -120, "privacy": -70, "terms": -70, "cookie": -70, "careers": -20,
    "career": -20, "blog": -18, "news": -14, "press": -12, "docs": -18,
}

_ROLE_PATTERNS = [
    ("about", ("about", "about-us", "company", "story", "mission", "who-we-are")),
    ("team", ("team", "leadership", "founders", "people")),
    ("product", ("product", "products", "platform", "solution", "solutions", "technology")),
]

_BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain"}


def _validate_public_hostname(hostname: str) -> None:
    normalized = hostname.rstrip(".").lower()
    if normalized in _BLOCKED_HOSTNAMES or normalized.endswith(".localhost") or normalized.endswith(".local") or normalized.endswith(".internal"):
        raise ValueError("公司官网必须使用可公开访问的互联网地址")
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return
    if not address.is_global:
        raise ValueError("公司官网不能指向内网、回环或保留地址")


def normalize_company_url(raw_url: str) -> str:
    value = (raw_url or "").strip()
    if not value:
        raise ValueError("请输入公司官网地址")
    if value.startswith("//"):
        value = f"https:{value}"
    elif "://" not in value:
        value = f"https://{value}"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("仅支持http或https网站地址")
    if not parsed.netloc:
        raise ValueError("请输入有效的公司官网地址")
    if parsed.username or parsed.password:
        raise ValueError("公司官网地址不能包含登录凭据")
    if not parsed.hostname:
        raise ValueError("请输入有效的公司官网地址")
    _validate_public_hostname(parsed.hostname)
    normalized_path = (parsed.path or "").rstrip("/")
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), normalized_path, "", "", ""))


def validate_public_crawl_url(raw_url: str) -> str:
    normalized_url = normalize_company_url(raw_url)
    parsed = urlparse(normalized_url)
    hostname = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        resolved = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError(f"域名解析失败：{hostname}") from exc
    if not resolved:
        raise ValueError(f"域名没有可用地址：{hostname}")
    for family, _, _, _, sockaddr in resolved:
        if family not in {socket.AF_INET, socket.AF_INET6}:
            continue
        address = ipaddress.ip_address(sockaddr[0])
        if not address.is_global:
            raise ValueError("域名解析到了内网、回环或保留地址")
    return normalized_url


def _same_domain(left: str, right: str) -> bool:
    return urlparse(left).netloc.lower() == urlparse(right).netloc.lower()


def _path_depth(path: str) -> int:
    return len([part for part in path.split("/") if part])


def _clean_anchor_title(title: Optional[str], href: str) -> str:
    text = re.sub(r"\s+", " ", (title or "").strip())
    if text:
        return text[:80]
    path = urlparse(href).path.strip("/")
    if not path:
        return "首页"
    return path.split("/")[-1][:80]


def _score_link(href: str, title: str) -> int:
    path = urlparse(href).path.lower().strip("/")
    segments = [seg for seg in re.split(r"[-_/]+", path) if seg]
    score = 0
    for seg in segments:
        score += _POSITIVE_KEYWORDS.get(seg, 0)
        score += _NEGATIVE_KEYWORDS.get(seg, 0)
    if not segments:
        score += 30
    if len(segments) == 1:
        score += 12
    if len(segments) > 4:
        score -= 10
    if any(href.lower().endswith(ext) for ext in _ASSET_EXTENSIONS):
        score -= 100
    title_lower = (title or "").lower()
    for word, bonus in _POSITIVE_KEYWORDS.items():
        if word in title_lower:
            score += bonus // 3
    for word, penalty in _NEGATIVE_KEYWORDS.items():
        if word in title_lower:
            score += penalty // 3
    return score


def _classify_role(href: str, title: str) -> str:
    path = urlparse(href).path.lower().strip("/")
    segments = set(re.split(r"[-_/]+", path))
    segments.discard("")
    title_lower = (title or "").lower()
    for role, markers in _ROLE_PATTERNS:
        if any(marker in segments for marker in markers):
            return role
        if any(marker in title_lower for marker in markers):
            return role
    return "other"


def extract_candidate_links(base_url: str, html: str) -> list[dict]:
    from html.parser import HTMLParser

    class _LinkExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.links: list[tuple[str, str]] = []

        def handle_starttag(self, tag, attrs):
            if tag != "a":
                return
            href = None
            title = None
            for name, value in attrs:
                if name == "href" and value:
                    href = value.strip()
                elif name == "title" and value:
                    title = value.strip()
            if href:
                self.links.append((href, title or ""))

    parser = _LinkExtractor()
    parser.feed(html)

    seen = set()
    candidates = []
    for href, title in parser.links:
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        if href.startswith("/"):
            full_url = urlunparse((urlparse(base_url).scheme, urlparse(base_url).netloc, href, "", "", ""))
        elif href.startswith("http"):
            full_url = href
        else:
            continue
        if not _same_domain(full_url, base_url):
            continue
        if full_url in seen:
            continue
        seen.add(full_url)
        clean_title = _clean_anchor_title(title, full_url)
        score = _score_link(full_url, title)
        role = _classify_role(full_url, title)
        candidates.append({"url": full_url, "title": clean_title, "score": score, "role": role, "depth": _path_depth(urlparse(full_url).path)})
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates


def select_pages(candidates: list[dict], max_pages: int = 6) -> list[dict]:
    role_priority = {"homepage": 0, "about": 1, "team": 2, "product": 3, "other": 4}
    by_role: dict[str, list[dict]] = {}
    for c in candidates:
        role = c["role"]
        by_role.setdefault(role, []).append(c)

    selected: list[dict] = []
    homepage = candidates[0] if candidates else None
    if homepage:
        selected.append({**homepage, "role": "homepage"})

    for role in ["about", "team", "product"]:
        pool = by_role.get(role, [])
        if pool:
            selected.append(pool[0])

    for c in candidates:
        if c in selected:
            continue
        if len(selected) >= max_pages:
            break
        selected.append(c)

    selected.sort(key=lambda c: role_priority.get(c["role"], 9))
    return selected[:max_pages]


def ingest_company_website(url: str, company_name: str = "") -> dict:
    normalized_url = validate_public_crawl_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GEO-Platform/1.0; +https://github.com/wood-poplar/geo-platform)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    resp = requests.get(normalized_url, headers=headers, timeout=15, allow_redirects=True, verify=True)
    # chardet对中文页面可能误检为Windows-1254等，优先按utf-8解码，失败再回退自动检测
    try:
        html = resp.content.decode("utf-8")
    except UnicodeDecodeError:
        resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
    final_url = resp.url

    candidates = extract_candidate_links(final_url, html)
    selected = select_pages(candidates)

    return {
        "url": normalized_url,
        "final_url": final_url,
        "status_code": resp.status_code,
        "title": _extract_title(html),
        "page_count": len(selected),
        "pages": [{"url": p["url"], "title": p["title"], "role": p["role"], "score": p["score"]} for p in selected],
    }


def _extract_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()[:120]
    return ""
