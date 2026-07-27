from __future__ import annotations

import concurrent.futures
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml


ROOT = Path(r"E:\awnav\awnav.com")
DATA_FILE = ROOT / "data" / "overseas_marketing.yml"
OUTPUT_DIR = ROOT / "content" / "ad-marketing-pages"
CACHE_DIR = ROOT / ".cache" / "007-tool-pages"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
}


TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
META_DESCRIPTION_RE = re.compile(
    r'<meta\s+name="description"\s+content="(.*?)"', re.S | re.I
)
JSON_LD_RE = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>', re.S | re.I
)
OFFICIAL_URL_RE = re.compile(
    r'<a href="([^"]+)"[^>]*>\s*访问官网', re.S | re.I
)
SECTION_RE_TEMPLATE = r"<section[^>]*>\s*<h2[^>]*>\s*{label}\s*</h2>(.*?)</section>"
PROS_CONS_BLOCK_RE = re.compile(
    r"<h3[^>]*>\s*(优点|缺点)\s*</h3>\s*<ul[^>]*>(.*?)</ul>", re.S | re.I
)
PARAGRAPH_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S | re.I)
LIST_ITEM_RE = re.compile(r"<li[^>]*>(.*?)</li>", re.S | re.I)
RELATED_ANCHOR_RE = re.compile(
    r'<a href="/tools/([^"]+)" class="group flex items-start gap-3">(.*?)</a>',
    re.S | re.I,
)
IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"[^>]+alt="([^"]+)"', re.S | re.I)
RELATED_TITLE_RE = re.compile(r"<h3[^>]*>(.*?)</h3>", re.S | re.I)
RELATED_DESC_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"[ \t\r\f\v]+")
SAFE_ASCII_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def slug_from_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value or "")
    path = parsed.path.rstrip("/")
    slug = path.split("/")[-1] if path else ""
    return urllib.parse.unquote(slug).strip()


def local_route_for_slug(source_slug: str) -> str:
    encoded_slug = urllib.parse.quote(source_slug, safe="-_.~")
    return f"/ad-marketing/{encoded_slug}/"


def file_stem_for_slug(source_slug: str) -> str:
    lower_slug = source_slug.lower()
    if SAFE_ASCII_RE.match(lower_slug):
        return lower_slug
    digest = hashlib.md5(source_slug.encode("utf-8")).hexdigest()[:12]
    return f"tool-{digest}"


def cache_path_for_slug(source_slug: str) -> Path:
    return CACHE_DIR / f"{file_stem_for_slug(source_slug)}.html"


def strip_tags(value: str) -> str:
    text = value or ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = TAG_RE.sub("", text)
    return html.unescape(text).strip()


def normalize_inline_text(value: str) -> str:
    cleaned = strip_tags(value)
    lines = []
    for raw_line in cleaned.splitlines():
        compact = SPACE_RE.sub(" ", raw_line).strip()
        if compact:
            lines.append(compact)
    return "\n".join(lines).strip()


def first_paragraph(value: str) -> str:
    paragraphs = extract_paragraphs(value)
    if paragraphs:
        return paragraphs[0]
    return normalize_inline_text(value)


def extract_paragraphs(section_html: str) -> list[str]:
    paragraphs = []
    for raw in PARAGRAPH_RE.findall(section_html or ""):
        text = normalize_inline_text(raw)
        if text:
            paragraphs.append(text)
    if paragraphs:
        return paragraphs
    fallback = normalize_inline_text(section_html or "")
    return [fallback] if fallback else []


def extract_list_items(section_html: str) -> list[str]:
    items = []
    for raw in LIST_ITEM_RE.findall(section_html or ""):
        text = normalize_inline_text(raw)
        if text:
            items.append(text)
    return items


def fetch_html(source_slug: str, source_url: str) -> str:
    cache_path = cache_path_for_slug(source_slug)
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(source_url, headers=REQUEST_HEADERS)
    last_error: Exception | None = None

    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                html_text = response.read().decode("utf-8", errors="ignore")
            cache_path.write_text(html_text, encoding="utf-8")
            return html_text
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(f"failed to fetch {source_url}: {last_error}") from last_error


def extract_json_ld(html_text: str) -> list[dict]:
    blocks: list[dict] = []
    for raw in JSON_LD_RE.findall(html_text):
        payload = html.unescape(raw).strip()
        if not payload:
            continue
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            blocks.extend(item for item in data if isinstance(item, dict))
        elif isinstance(data, dict):
            blocks.append(data)
    return blocks


def extract_app(blocks: list[dict]) -> dict:
    for block in blocks:
        if block.get("@type") == "SoftwareApplication":
            return block
    return {}


def extract_faqs(blocks: list[dict]) -> list[dict]:
    for block in blocks:
        if block.get("@type") != "FAQPage":
            continue
        faqs = []
        for entity in block.get("mainEntity", []) or []:
            if not isinstance(entity, dict):
                continue
            question = normalize_inline_text(entity.get("name", ""))
            answer = normalize_inline_text(
                ((entity.get("acceptedAnswer") or {}).get("text")) or ""
            )
            if question and answer:
                faqs.append({"question": question, "answer": answer})
        return faqs
    return []


def extract_reviews(app: dict) -> list[dict]:
    reviews = []
    for review in app.get("review", []) or []:
        if not isinstance(review, dict):
            continue
        author = normalize_inline_text(
            ((review.get("author") or {}).get("name")) or ""
        )
        body = normalize_inline_text(review.get("reviewBody") or "")
        rating = str(((review.get("reviewRating") or {}).get("ratingValue")) or "").strip()
        if author and body:
            reviews.append({"author": author, "body": body, "rating": rating})
    return reviews


def extract_section_html(label: str, html_text: str) -> str:
    pattern = re.compile(
        SECTION_RE_TEMPLATE.format(label=re.escape(label)),
        re.S | re.I,
    )
    match = pattern.search(html_text)
    return match.group(1) if match else ""


def extract_related(section_html: str) -> list[dict]:
    related = []
    seen: set[str] = set()
    for source_slug, anchor_html in RELATED_ANCHOR_RE.findall(section_html or ""):
        decoded_slug = urllib.parse.unquote(source_slug).strip().strip("/")
        if not decoded_slug or decoded_slug in seen:
            continue
        seen.add(decoded_slug)
        img_match = IMG_RE.search(anchor_html)
        title_match = RELATED_TITLE_RE.search(anchor_html)
        desc_match = RELATED_DESC_RE.search(anchor_html)
        title = normalize_inline_text(title_match.group(1)) if title_match else decoded_slug
        description = normalize_inline_text(desc_match.group(1)) if desc_match else ""
        logo = html.unescape(img_match.group(1)).strip() if img_match else ""
        alt = normalize_inline_text(img_match.group(2)) if img_match else ""
        related.append(
            {
                "sourceSlug": decoded_slug,
                "title": title or alt or decoded_slug,
                "description": description,
                "logo": logo,
                "url": local_route_for_slug(decoded_slug),
            }
        )
    return related


def build_source_url(source_slug: str) -> str:
    encoded = urllib.parse.quote(source_slug, safe="-_.~")
    return f"https://007.co.com/tools/{encoded}/"


def parse_tool(item: dict) -> dict:
    source_slug = item["sourceSlug"]
    source_url = item["sourceUrl"]
    html_text = fetch_html(source_slug, source_url)
    blocks = extract_json_ld(html_text)
    app = extract_app(blocks)

    title_match = TITLE_RE.search(html_text)
    meta_match = META_DESCRIPTION_RE.search(html_text)
    detail_html = extract_section_html("详细介绍", html_text)
    pricing_html = extract_section_html("定价信息", html_text)
    pros_cons_html = extract_section_html("优缺点分析", html_text)
    related_html = extract_section_html("相关工具", html_text)

    seo_title = (
        normalize_inline_text(title_match.group(1))
        if title_match
        else f"{item['title']} - 详细介绍与评价"
    )
    detail_paragraphs = extract_paragraphs(detail_html)
    detail_text = "\n\n".join(detail_paragraphs)
    meta_description = (
        normalize_inline_text(meta_match.group(1))
        if meta_match
        else normalize_inline_text(app.get("description") or "")
    )

    official_url_match = OFFICIAL_URL_RE.search(html_text)
    official_url = normalize_inline_text(app.get("url") or "")
    if not official_url and official_url_match:
        official_url = official_url_match.group(1).strip()
    if not official_url:
        official_url = source_url

    pros: list[str] = []
    cons: list[str] = []
    for kind, block_html in PROS_CONS_BLOCK_RE.findall(pros_cons_html):
        items = extract_list_items(block_html)
        if kind == "优点":
            pros = items
        elif kind == "缺点":
            cons = items

    pricing = first_paragraph(pricing_html)
    app_description = normalize_inline_text(app.get("description") or "")

    return {
        "sourceSlug": source_slug,
        "title": normalize_inline_text(app.get("name") or "") or item["title"],
        "description": item["description"],
        "metaDescription": meta_description or item["description"] or app_description,
        "seoTitle": seo_title,
        "sourceUrl": source_url,
        "officialUrl": official_url,
        "logo": item["logo"],
        "category": item["category"],
        "pricing": pricing or normalize_inline_text(((app.get("offers") or {}).get("description")) or ""),
        "ratingValue": str(((app.get("aggregateRating") or {}).get("ratingValue")) or "").strip(),
        "reviewCount": str(((app.get("aggregateRating") or {}).get("reviewCount")) or "").strip(),
        "applicationCategory": normalize_inline_text(app.get("applicationCategory") or ""),
        "pros": pros,
        "cons": cons,
        "reviews": extract_reviews(app),
        "faqs": extract_faqs(blocks),
        "related": extract_related(related_html),
        "body": detail_text or app_description or item["description"],
        "status": "ok",
    }


def build_frontmatter(tool: dict) -> str:
    frontmatter = {
        "title": tool["title"],
        "description": tool["description"],
        "seoTitle": tool["seoTitle"],
        "layout": "tool-detail",
        "url": local_route_for_slug(tool["sourceSlug"]),
        "slug": tool["sourceSlug"],
        "sourceUrl": tool["sourceUrl"],
        "officialUrl": tool["officialUrl"],
        "logo": tool["logo"],
        "category": tool["category"],
        "pricing": tool["pricing"],
        "ratingValue": tool["ratingValue"],
        "reviewCount": tool["reviewCount"],
        "applicationCategory": tool["applicationCategory"],
        "pros": tool["pros"],
        "cons": tool["cons"],
        "reviews": tool["reviews"],
        "faqs": tool["faqs"],
        "related": tool["related"],
    }
    return yaml.safe_dump(
        frontmatter,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=1000,
    ).strip()


def write_tool_page(tool: dict) -> None:
    output_path = OUTPUT_DIR / f"{file_stem_for_slug(tool['sourceSlug'])}.md"
    markdown = f"---\n{build_frontmatter(tool)}\n---\n\n{tool['body'].strip()}\n"
    output_path.write_text(markdown, encoding="utf-8")


def collect_items(sections: list[dict]) -> tuple[list[dict], dict[str, str]]:
    items: list[dict] = []
    route_by_source_slug: dict[str, str] = {}

    for section in sections:
        category = section["taxonomy"]
        for link in section["links"]:
            source_slug = slug_from_url(link.get("source_url") or link.get("url") or "")
            if not source_slug:
                continue
            source_url = build_source_url(source_slug)
            local_url = local_route_for_slug(source_slug)
            link["source_url"] = source_url
            link["url"] = local_url
            route_by_source_slug[source_slug] = local_url
            items.append(
                {
                    "sourceSlug": source_slug,
                    "title": link["title"],
                    "logo": link["logo"],
                    "description": link["description"],
                    "sourceUrl": source_url,
                    "category": category,
                }
            )

    deduped = {item["sourceSlug"]: item for item in items}
    return list(deduped.values()), route_by_source_slug


def localize_related_urls(results: list[dict], route_by_source_slug: dict[str, str]) -> None:
    for tool in results:
        localized_related = []
        for related in tool.get("related", []):
            source_slug = related["sourceSlug"]
            related["url"] = route_by_source_slug.get(source_slug, build_source_url(source_slug))
            localized_related.append(related)
        tool["related"] = localized_related


def fallback_tool(item: dict, error: Exception) -> dict:
    message = (
        "该工具详情页暂时未能完成同步，你仍然可以通过下方按钮访问原始页面继续查看。\n\n"
        f"同步来源：{item['sourceUrl']}\n\n"
        f"抓取错误：{error}"
    )
    return {
        "sourceSlug": item["sourceSlug"],
        "title": item["title"],
        "description": item["description"],
        "metaDescription": item["description"],
        "seoTitle": f"{item['title']} - 详细介绍与评价",
        "sourceUrl": item["sourceUrl"],
        "officialUrl": item["sourceUrl"],
        "logo": item["logo"],
        "category": item["category"],
        "pricing": "",
        "ratingValue": "",
        "reviewCount": "",
        "applicationCategory": "",
        "pros": [],
        "cons": [],
        "reviews": [],
        "faqs": [],
        "related": [],
        "body": message,
        "status": "fallback",
    }


def main() -> None:
    sections = yaml.safe_load(DATA_FILE.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for existing in OUTPUT_DIR.glob("*.md"):
        existing.unlink()

    items, route_by_source_slug = collect_items(sections)
    results: list[dict] = []

    def worker(payload: dict) -> dict:
        try:
            return parse_tool(payload)
        except Exception as exc:  # noqa: BLE001
            return fallback_tool(payload, exc)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, item) for item in items]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda item: item["sourceSlug"])
    localize_related_urls(results, route_by_source_slug)

    for tool in results:
        write_tool_page(tool)

    DATA_FILE.write_text(
        yaml.safe_dump(
            sections,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=1000,
        ),
        encoding="utf-8",
    )

    ok_count = sum(1 for tool in results if tool["status"] == "ok")
    fallback_count = len(results) - ok_count
    print(f"Generated {len(results)} tool pages.")
    print(f"Successful: {ok_count}")
    print(f"Fallback: {fallback_count}")
    print(f"Updated {len(sections)} categories in {DATA_FILE}.")


if __name__ == "__main__":
    main()
