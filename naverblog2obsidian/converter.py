"""HTML → 옵시디언 마크다운 변환 모듈"""

import re
from typing import Dict, List, Optional

from bs4 import BeautifulSoup, Tag
from markdownify import MarkdownConverter


class NaverMarkdownConverter(MarkdownConverter):
    """네이버 블로그 HTML에 최적화된 마크다운 변환기"""

    def convert_blockquote(self, el, text, **kwargs):
        """인용문 변환"""
        lines = text.strip().splitlines()
        return "\n" + "\n".join(f"> {line}" for line in lines) + "\n\n"

    def convert_img(self, el, text, **kwargs):
        """이미지 태그 변환 — src 추출"""
        src = el.get("data-lazy-src") or el.get("src") or ""
        alt = el.get("alt", "")
        if not src or "blank" in src or src.startswith("data:"):
            return ""
        return f"![{alt}]({src})\n\n"

    def convert_br(self, el, text, **kwargs):
        return "\n"


def extract_hashtags(soup: Optional[BeautifulSoup]) -> List[str]:
    """본문에서 해시태그 추출

    Args:
        soup: 본문 BeautifulSoup 객체

    Returns:
        태그 문자열 리스트
    """
    if not soup:
        return []

    tags = []
    # 네이버 블로그 해시태그: class="post_tag" 또는 #태그 패턴
    tag_area = soup.find("div", class_="post_tag") or soup.find(
        "div", class_="se_tag"
    )
    if tag_area:
        for a_tag in tag_area.find_all("a"):
            text = a_tag.get_text(strip=True).lstrip("#")
            if text:
                tags.append(text)

    # 본문 내 인라인 해시태그
    if not tags:
        text = soup.get_text()
        inline_tags = re.findall(r"#(\w+)", text)
        tags = [t for t in inline_tags if len(t) > 1]

    return list(dict.fromkeys(tags))  # 중복 제거, 순서 유지


def extract_images(soup: Optional[BeautifulSoup]) -> List[str]:
    """본문에서 이미지 URL 추출

    Args:
        soup: 본문 BeautifulSoup 객체

    Returns:
        이미지 URL 리스트
    """
    if not soup:
        return []

    urls = []
    for img in soup.find_all("img"):
        src = img.get("data-lazy-src") or img.get("src") or ""
        if src and "blank" not in src and not src.startswith("data:"):
            # 리사이즈 파라미터 제거하여 원본 이미지 URL 확보
            src = re.sub(r"\?type=.*$", "", src)
            urls.append(src)

    return list(dict.fromkeys(urls))  # 중복 제거


def html_to_markdown(soup: Optional[BeautifulSoup]) -> str:
    """HTML을 마크다운으로 변환

    Args:
        soup: 본문 BeautifulSoup 객체

    Returns:
        마크다운 문자열
    """
    if not soup:
        return ""

    # 불필요한 요소 제거
    for tag_name in ["script", "style", "noscript"]:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # 구분선 요소 → <hr> 변환
    for div in soup.find_all("div", class_="se-section-delimiter"):
        div.replace_with(soup.new_tag("hr"))

    # 해시태그 영역 제거 (frontmatter로 이동하므로)
    for tag_area in soup.find_all("div", class_=["post_tag", "se_tag"]):
        tag_area.decompose()

    # 변환
    html_str = str(soup)
    md = NaverMarkdownConverter(
        heading_style="atx",
        bullets="-",
        strip=["span"],
    ).convert(html_str)

    # 정리
    md = re.sub(r"\n{3,}", "\n\n", md)  # 3줄 이상 빈 줄 → 2줄
    md = md.strip()

    return md


def build_frontmatter(
    title: str,
    date: str,
    url: str,
    category: str = "",
    tags: Optional[List[str]] = None,
) -> str:
    """옵시디언 YAML frontmatter 생성

    Args:
        title: 글 제목
        date: 작성일
        url: 원본 URL
        category: 카테고리명
        tags: 태그 리스트

    Returns:
        YAML frontmatter 문자열
    """
    # 날짜 정규화: "2024. 3. 24." → "2024-03-24"
    date_normalized = ""
    date_match = re.match(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", date)
    if date_match:
        y, m, d = date_match.groups()
        date_normalized = f"{y}-{int(m):02d}-{int(d):02d}"

    # 제목에서 YAML 특수문자 이스케이프
    safe_title = title.replace('"', '\\"')

    lines = ["---"]
    lines.append(f'title: "{safe_title}"')
    if date_normalized:
        lines.append(f"date: {date_normalized}")
    lines.append(f"source: \"{url}\"")
    if category:
        lines.append(f'category: "{category}"')
    if tags:
        tag_str = ", ".join(tags)
        lines.append(f"tags: [{tag_str}]")
    lines.append("---")

    return "\n".join(lines)


def convert_post(
    title: str,
    date: str,
    html_soup: Optional[BeautifulSoup],
    url: str,
    category: str = "",
) -> str:
    """글 전체를 옵시디언 마크다운으로 변환

    Args:
        title: 글 제목
        date: 작성일
        html_soup: 본문 BeautifulSoup
        url: 원본 URL
        category: 카테고리명

    Returns:
        완성된 옵시디언 마크다운 문자열
    """
    tags = extract_hashtags(html_soup)
    frontmatter = build_frontmatter(title, date, url, category, tags)
    body = html_to_markdown(html_soup)

    return f"{frontmatter}\n\n# {title}\n\n{body}\n"
