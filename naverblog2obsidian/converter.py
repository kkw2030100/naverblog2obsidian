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
    for tag_name in ["script", "style", "noscript", "iframe"]:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # 네이버 블로그 UI 요소 제거 (프로파일, 공유, 신고, 이웃추가 등)
    remove_classes = [
        "blog_author_profile",  # 프로파일 영역
        "blog2_series",         # 시리즈
        "post_author",          # 작성자
        "se_author",            # 작성자
        "se_publishDate",       # 날짜
        "blog_date",            # 날짜
        "post_tag",             # 태그 (frontmatter로 이동)
        "se_tag",               # 태그
        "btn_share",            # 공유 버튼
        "post_footer",          # 하단 버튼들
        "post_header",          # 상단 헤더
        "se-section-oglink",    # OG 링크 프리뷰
    ]
    for cls in remove_classes:
        for el in soup.find_all(class_=cls):
            el.decompose()

    # 카테고리 링크 제거 (PostList.naver 링크)
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "PostList.naver" in href or "이웃추가" in a.get_text() or "공유하기" in a.get_text() or "신고하기" in a.get_text() or "URL 복사" in a.get_text():
            a.decompose()

    # 프로파일 이미지+블로그명 링크 제거
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "blog.naver.com/" in href:
            # 프로파일 이미지가 포함된 링크
            if a.find("img"):
                text = a.get_text(strip=True)
                if not text or len(text) < 30:
                    a.decompose()
                    continue
            # 블로그 메인 링크 (블로그명만 있는 짧은 링크)
            text = a.get_text(strip=True)
            if text and len(text) < 20 and not a.find("img"):
                # "메르", "데이터는알고있다" 등 블로그명
                if re.match(r"^https?://blog\.naver\.com/\w+/?$", href):
                    a.decompose()

    # "본문 기타 기능" 등 잡다한 UI 텍스트 포함 요소 제거
    for el in soup.find_all(string=re.compile(r"(본문 기타 기능|이웃추가|URL 복사|공유하기|신고하기)")):
        parent = el.parent
        if parent and parent.name in ("a", "span", "div", "button"):
            parent.decompose()

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
    md = re.sub(r"^\s*\*・\*\s*$", "", md, flags=re.MULTILINE)  # "・" 구분자 제거
    md = re.sub(r"^\s*​\s*$", "", md, flags=re.MULTILINE)  # 네이버 빈 문자(​) 줄 제거
    md = re.sub(r"\n{3,}", "\n\n", md)  # 다시 정리
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
    # 날짜 정규화
    from .utils import normalize_date
    date_normalized = normalize_date(date) if date else ""

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

    # 본문에서 제목과 유사한 텍스트 줄 제거 (중복 방지)
    import unicodedata
    def _normalize_title(t):
        """제목 비교용 정규화: 공백/특수문자 무시"""
        t = re.sub(r'[#\s?？!！.,·\u200b\u200c\u200d\ufeff]', '', t)
        return t.lower()

    lines = body.split("\n")
    cleaned_lines = []
    title_norm = _normalize_title(title)
    removed_count = 0
    for line in lines:
        line_norm = _normalize_title(line)
        if removed_count < 3 and line_norm and title_norm and line_norm == title_norm:
            removed_count += 1
            continue
        cleaned_lines.append(line)
    body = "\n".join(cleaned_lines).strip()

    return f"{frontmatter}\n\n# {title}\n\n{body}\n"
