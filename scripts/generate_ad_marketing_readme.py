from __future__ import annotations

import html
import re
import urllib.parse
from pathlib import Path

import yaml


ROOT = Path(r"E:\awnav\awnav.com")
DATA_FILE = ROOT / "data" / "overseas_marketing.yml"
PAGES_DIR = ROOT / "content" / "ad-marketing-pages"
README_FILE = ROOT / "README.md"
SITE_URL = "https://awnav.com/ad-marketing/"
ASSET_BASE_URL = "https://awnav.com"
DEFAULT_ICON_URL = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f310.svg"


def github_anchor(text: str) -> str:
    value = text.strip().lower()
    value = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", value)
    value = re.sub(r"\s+", "-", value)
    return value


def slug_from_local_url(url: str) -> str:
    path = urllib.parse.urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1] if path else ""
    return urllib.parse.unquote(slug)


def normalize_logo_url(value: str) -> str:
    if not value:
        return ""
    if value.startswith("/"):
        return f"{ASSET_BASE_URL}{value}"
    return value


def favicon_url_for_readme(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return DEFAULT_ICON_URL
    parsed = urllib.parse.urlparse(value if re.match(r"^https?://", value, re.I) else f"https://{value}")
    if not parsed.netloc:
        return DEFAULT_ICON_URL
    domain_url = urllib.parse.quote(f"{parsed.scheme}://{parsed.netloc}", safe="")
    return f"https://www.google.com/s2/favicons?domain_url={domain_url}&sz=32"


def load_page_frontmatter() -> dict[str, dict]:
    pages: dict[str, dict] = {}
    for path in PAGES_DIR.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        parts = text.split("---\n", 2)
        if len(parts) < 3:
            continue
        frontmatter = yaml.safe_load(parts[1]) or {}
        slug = str(frontmatter.get("slug", "")).strip()
        if slug:
            pages[slug] = frontmatter
    return pages


def platform_icon_cell(name: str, logo_url: str) -> str:
    safe_name = html.escape(name, quote=True)
    safe_logo_url = html.escape(logo_url, quote=True)
    return (
        f'<img src="{safe_logo_url}" width="18" alt="{safe_name}" '
        'style="display:block;margin:0 auto;background:#fff;border-radius:4px;">'
    )


def build_readme() -> str:
    sections = yaml.safe_load(DATA_FILE.read_text(encoding="utf-8"))
    pages = load_page_frontmatter()

    lines: list[str] = [
        "<!--",
        " * @Description:",
        " * @telegram: awnav.com",
        " **关键词：**",
        "出海广告营销导航, AI工具导航, 社交媒体营销工具, 跨境电商工具, 广告投放工具, Facebook广告工具, Google广告工具, 指纹浏览器, 海外支付工具, 海外接码平台, 海外网络工具, 内容制作工具, SEO工具导航, 独立站运营工具, 跨境服务平台",
        "",
        "**Description：**",
        "本仓库整理 awnav 出海广告营销导航相关资源，覆盖 AI 工具、社交媒体、跨境电商、广告投放、指纹浏览器、海外网络、支付工具、内容制作、开发工具与跨境服务等分类合集，适合做工具导航、SEO 聚合与 GitHub 仓库展示。",
        "-->",
        '<div align="center">',
        "",
        "# 出海广告营销导航、AI工具、社交媒体、跨境电商与广告投放工具大全",
        "",
        "#### 持续整理 AI 工具、社交媒体营销、跨境电商、广告投放、指纹浏览器、海外网络、支付工具与开发资源，方便快速找工具、比功能、做同域 SEO 沉淀。",
        "",
        f"### 导航网站: [{SITE_URL}]({SITE_URL})",
        "",
        "</div>",
        "",
        "## 目录",
        "",
    ]

    for section in sections:
        title = section["taxonomy"]
        lines.append(f"- [{title}](#{github_anchor(title)})")

    lines.append("")

    section_icons = {
        "OpenClaw": "1f916",
        "AI工具": "1f9e0",
        "社交媒体": "1f4f1",
        "跨境电商": "1f6d2",
        "营销推广": "1f4e3",
        "Facebook": "1f4d8",
        "Google": "1f50e",
        "广告工具": "1f3af",
        "指纹浏览器": "1f9ed",
        "海外网络": "1f310",
        "海外接码": "1f4e9",
        "海外支付": "1f4b3",
        "数字货币": "1fa99",
        "内容制作": "1f3ac",
        "实用工具": "1f9f0",
        "跨境资讯": "1f4f0",
        "开发工具": "1f4bb",
        "引流工具": "1f680",
        "跨境服务": "1f91d",
    }

    for section in sections:
        title = section["taxonomy"]
        icon = section_icons.get(title)
        if icon:
            lines.append(
                f'## <img src="https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/{icon}.svg" width="18" alt="{title}"> {title}'
            )
        else:
            lines.append(f"## {title}")
        lines.append("")
        lines.append("| 图标 | 平台名称 | 官网链接 | 功能特点 |")
        lines.append("| :---: | --- | --- | --- |")

        for item in section["links"]:
            name = str(item.get("title", "")).replace("|", "/").strip()
            local_url = str(item.get("url", "")).strip()
            slug = slug_from_local_url(local_url)
            frontmatter = pages.get(slug, {})
            jump_url = str(
                frontmatter.get("officialUrl")
                or frontmatter.get("sourceUrl")
                or local_url
            ).strip()
            logo_url = favicon_url_for_readme(jump_url)
            desc = " ".join(str(item.get("description", "")).replace("|", "/").split())
            lines.append(
                f"| {platform_icon_cell(name, logo_url)} | {name} | [{jump_url}]({jump_url}) | {desc} |"
            )

        lines.append("")

    lines.extend(
        [
            "## 说明",
            "",
            f"- 本文档内容来源于 [{SITE_URL}]({SITE_URL}) 当前导航数据导出。",
            "- 表格中的官网链接优先使用每个详情页里的访问官网地址。",
            "- 如果某条没有抓到官网地址，则回退到原始来源链接。",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    README_FILE.write_text(build_readme(), encoding="utf-8")
    print(README_FILE)


if __name__ == "__main__":
    main()
