"""유틸리티 함수"""

import os
import re


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """파일/폴더명으로 사용할 수 없는 문자 제거

    Args:
        name: 원본 문자열
        max_length: 최대 길이

    Returns:
        정리된 문자열
    """
    # 파일명 금지 문자 제거
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    # 앞뒤 공백/점 제거
    name = name.strip().strip(".")
    # 연속 공백 → 단일 공백
    name = re.sub(r"\s+", " ", name)
    # 길이 제한
    if len(name) > max_length:
        name = name[:max_length].rstrip()
    return name or "Untitled"


def normalize_date(date_str: str) -> str:
    """날짜 문자열 정규화

    Args:
        date_str: "2024. 3. 24." 또는 "2024.03.24" 형태

    Returns:
        "2024-03-24" 형태
    """
    match = re.match(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", date_str)
    if match:
        y, m, d = match.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"
    return date_str.strip()


def make_post_filename(date: str, title: str) -> str:
    """글 파일명 생성: "YYYY-MM-DD 제목.md"

    Args:
        date: 작성일 (원본 형식)
        title: 글 제목

    Returns:
        파일명 문자열
    """
    normalized_date = normalize_date(date)
    safe_title = sanitize_filename(title)
    return f"{normalized_date} {safe_title}.md"


def sanitize_folder_name(name: str) -> str:
    """카테고리명을 폴더명으로 변환

    Args:
        name: 카테고리명

    Returns:
        폴더명 문자열
    """
    name = sanitize_filename(name)
    # 슬래시 → 언더스코어 (이미 sanitize_filename에서 제거되지만 혹시 모를 경우)
    name = name.replace("/", "_")
    return name


def ensure_dir(path: str):
    """디렉토리가 없으면 생성"""
    os.makedirs(path, exist_ok=True)
