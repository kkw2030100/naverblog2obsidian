"""AI 기반 옵시디언 스타일 포맷터

변환된 마크다운을 AI가 옵시디언 최적화 형태로 재구성합니다.
- Callouts (> [!info], > [!tip], > [!warning] 등)
- 이모지 헤더
- 테이블 정리
- 핵심 요약
- 체크리스트
"""

import json
import os
import re
from typing import Optional

SYSTEM_PROMPT = """당신은 블로그 글을 옵시디언(Obsidian) 마크다운으로 변환하는 전문가입니다.

## 변환 규칙

### 1. Properties (YAML frontmatter)
글 맨 위에 반드시 포함:
```
---
title: "제목"
date: YYYY-MM-DD
source: "원본 URL"
category: "카테고리"
tags: [태그1, 태그2]
---
```

### 2. 핵심 요약 Callout
Properties 바로 아래에 핵심 요약을 넣으세요:
```
> [!info] 핵심 요약
> - 요약 포인트 1
> - 요약 포인트 2
> - 요약 포인트 3
```

### 3. Callout 종류 활용
내용에 맞게 다양한 callout을 사용하세요:
- `> [!info]` — 정보, 요약
- `> [!tip]` 또는 `> [!tip] 💡 제목` — 팁, 조언, 실천 사항
- `> [!warning]` 또는 `> [!warning] ⚠️ 제목` — 경고, 주의사항, 위기
- `> [!quote]` — 인용문, 명언
- `> [!success]` 또는 `> [!success] ✅ 제목` — 성과, 결과
- `> [!note]` 또는 `> [!note] 📝 제목` — 참고사항
- `> [!example]` — 예시

### 4. 이모지 헤더
모든 ## 헤더에 관련 이모지를 붙이세요:
- `## 🔴 위기/문제 상황`
- `## 🎯 목표/전략`
- `## 💎 핵심 인사이트`
- `## 🏆 결과/성과`
- `## 🔥 액션 아이템`
- `## 📊 데이터/분석`

### 5. 테이블
비교, 목록, 수치 데이터는 테이블로 정리

### 6. ==하이라이트==
핵심 키워드나 중요 문장에 ==하이라이트== 사용

### 7. 체크리스트
실천사항이나 할 일은 체크리스트로:
- [ ] 실천사항 1
- [ ] 실천사항 2

### 8. 금지사항
- `---` (수평선) 사용 금지! (frontmatter 외에는 절대 사용하지 마세요)
- 코드블록(```) 사용 금지
- 원본 내용을 임의로 삭제하지 마세요
- 의미를 왜곡하지 마세요

### 9. 구조 (가장 중요!)
- ⚠️ 원본 글의 모든 내용을 빠짐없이 포함해야 합니다! 절대 요약하거나 생략하지 마세요!
- 원본의 모든 문장, 수치, 이름, 날짜를 그대로 유지
- 긴 문단은 불릿 포인트로 정리하되 내용은 생략하지 않기
- 핵심 메시지가 잘 드러나도록 구성
- 이미지 링크(![](url))도 원본 그대로 유지

입력으로 블로그 글의 마크다운 텍스트와 메타데이터가 주어집니다.
옵시디언 최적화된 마크다운을 출력하세요."""


def format_with_ai(
    markdown: str,
    title: str = "",
    date: str = "",
    source_url: str = "",
    category: str = "",
    tags: Optional[list] = None,
    provider: str = "openai",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """AI를 사용하여 마크다운을 옵시디언 스타일로 재구성

    Args:
        markdown: 원본 마크다운 텍스트
        title: 글 제목
        date: 작성일
        source_url: 원본 URL
        category: 카테고리명
        tags: 태그 리스트
        provider: AI 제공자 ("openai" 또는 "anthropic")
        model: 모델명 (None이면 기본값 사용)
        api_key: API 키 (None이면 환경변수에서 읽음)

    Returns:
        옵시디언 스타일로 재구성된 마크다운
    """
    # 메타데이터 구성
    meta = f"제목: {title}\n"
    if date:
        meta += f"작성일: {date}\n"
    if source_url:
        meta += f"원본 URL: {source_url}\n"
    if category:
        meta += f"카테고리: {category}\n"
    if tags:
        meta += f"태그: {', '.join(tags)}\n"

    user_prompt = f"""다음 블로그 글을 옵시디언 최적화 마크다운으로 변환해주세요.

## 메타데이터
{meta}

## 원본 글
{markdown}"""

    if provider == "anthropic":
        return _call_anthropic(user_prompt, model, api_key)
    else:
        return _call_openai(user_prompt, model, api_key)


def _call_openai(user_prompt: str, model: Optional[str], api_key: Optional[str]) -> str:
    """OpenAI API 호출"""
    import requests

    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "OpenAI API 키가 필요합니다. "
            "환경변수 OPENAI_API_KEY를 설정하거나 --api-key 옵션을 사용하세요."
        )

    mdl = model or "gpt-4o-mini"

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": mdl,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 8000,
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    # 코드블록으로 감싸진 경우 제거
    content = _strip_codeblock(content)
    return content


def _call_anthropic(user_prompt: str, model: Optional[str], api_key: Optional[str]) -> str:
    """Anthropic API 호출"""
    import requests

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError(
            "Anthropic API 키가 필요합니다. "
            "환경변수 ANTHROPIC_API_KEY를 설정하거나 --api-key 옵션을 사용하세요."
        )

    mdl = model or "claude-sonnet-4-20250514"

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": mdl,
            "max_tokens": 8000,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["content"][0]["text"]
    content = _strip_codeblock(content)
    return content


def _strip_codeblock(text: str) -> str:
    """AI 출력에서 코드블록 래핑 제거"""
    text = text.strip()
    if text.startswith("```markdown"):
        text = text[len("```markdown"):].strip()
    elif text.startswith("```md"):
        text = text[len("```md"):].strip()
    elif text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text
