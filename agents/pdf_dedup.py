"""PDF去重审计Agent — 蒸馏自郝攀文章中的重复PDF处理实践

问题：工业设备网站常见同一产品系列PDF被重复上传多次
方案：统一到下载中心 + 多对一301重定向保留旧地址权益
"""
from __future__ import annotations
import hashlib
import logging
import re
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)

PDF_SIGNATURE = b"%PDF"
MAX_PDF_SIZE = 50 * 1024 * 1024


def _download_pdf(url: str, timeout: int = 15) -> bytes:
    resp = requests.get(url, timeout=timeout, stream=True, headers={"User-Agent": "Mozilla/5.0 (compatible; GEO-Platform/1.0)"})
    resp.raise_for_status()
    content = resp.content
    if len(content) > MAX_PDF_SIZE:
        raise ValueError(f"PDF超过50MB限制: {len(content)} bytes")
    if not content[:5].startswith(PDF_SIGNATURE):
        raise ValueError("URL返回的不是PDF文件")
    return content


def _content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _extract_pdf_urls_from_html(html: str, base_domain: str = "") -> list:
    urls = set()
    for match in re.finditer(r'href=["\']([^"\']*\.pdf)["\']', html, re.IGNORECASE):
        url = match.group(1)
        if url.startswith("/"):
            url = f"https://{base_domain}{url}"
        elif not url.startswith("http"):
            continue
        urls.add(url)
    for match in re.finditer(r'src=["\']([^"\']*\.pdf)["\']', html, re.IGNORECASE):
        url = match.group(1)
        if url.startswith("/"):
            url = f"https://{base_domain}{url}"
        elif not url.startswith("http"):
            continue
        urls.add(url)
    return list(urls)


def audit_duplicate_pdfs(urls: list) -> dict:
    """审计PDF列表中的重复文件

    输入：PDF URL列表
    输出：去重报告，包含重复组和建议的301重定向规则
    """
    if not urls:
        return {"error": "PDF URL列表为空"}

    pdf_data = []
    errors = []

    for url in urls:
        try:
            content = _download_pdf(url)
            file_hash = _content_hash(content)
            pdf_data.append({"url": url, "hash": file_hash, "size": len(content)})
        except Exception as e:
            errors.append({"url": url, "error": str(e)})
            logger.warning("PDF下载失败 %s: %s", url, e)

    groups = {}
    for item in pdf_data:
        h = item["hash"]
        if h not in groups:
            groups[h] = []
        groups[h].append(item)

    duplicates = []
    unique = []
    for h, items in groups.items():
        if len(items) > 1:
            canonical = max(items, key=lambda x: x["size"])
            redirects = [item["url"] for item in items if item["url"] != canonical["url"]]
            duplicates.append({
                "hash": h[:16],
                "canonical_url": canonical["url"],
                "duplicate_urls": redirects,
                "duplicate_count": len(redirects),
                "file_size": canonical["size"],
                "redirect_rules": [{"from": url, "to": canonical["url"], "type": "301"} for url in redirects],
            })
        else:
            unique.append(items[0])

    return {
        "total_urls": len(urls),
        "successfully_downloaded": len(pdf_data),
        "errors": errors,
        "unique_pdfs": len(unique),
        "duplicate_groups": len(duplicates),
        "total_duplicates": sum(g["duplicate_count"] for g in duplicates),
        "duplicates": duplicates,
        "summary": {
            "wasted_space": sum(g["file_size"] * g["duplicate_count"] for g in duplicates),
            "recommended_redirects": sum(g["duplicate_count"] for g in duplicates),
            "canonical_pdfs": len(unique) + len(duplicates),
        },
    }


def audit_website_pdfs(domain: str) -> dict:
    """审计网站首页中引用的所有PDF"""
    normalized = domain.rstrip("/")
    if not normalized.startswith("http"):
        normalized = f"https://{normalized}"

    try:
        resp = requests.get(normalized, timeout=15, headers={"User-Agent": "Mozilla/5.0 (compatible; GEO-Platform/1.0)"})
        resp.raise_for_status()
    except Exception as e:
        return {"error": f"无法访问网站: {e}"}

    base_domain = urlparse(normalized).netloc
    pdf_urls = _extract_pdf_urls_from_html(resp.text, base_domain)

    if not pdf_urls:
        return {
            "domain": normalized,
            "pdfs_found": 0,
            "message": "首页未发现PDF链接。可手动提供PDF URL列表进行审计。",
        }

    audit = audit_duplicate_pdfs(pdf_urls)
    audit["domain"] = normalized
    audit["pdfs_found"] = len(pdf_urls)
    return audit
