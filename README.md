# 📝 naverblog2obsidian

**네이버 블로그 글을 옵시디언(Obsidian) 마크다운으로 변환하는 도구**

네이버 블로그에 쌓아온 소중한 글들을 옵시디언으로 옮기고 싶으신가요? `naverblog2obsidian`은 네이버 블로그 글을 자동으로 크롤링하여 옵시디언에 최적화된 마크다운 파일로 변환해줍니다.

## ✨ 주요 기능

- 🔄 **전체/카테고리별 백업** — 블로그 전체 또는 원하는 카테고리만 선택하여 변환
- 📋 **대화형 모드** — 옵션 없이 실행하면 친절하게 하나씩 물어봅니다
- 🏷️ **옵시디언 Properties** — YAML frontmatter 자동 생성 (제목, 날짜, 카테고리, 태그)
- 🖼️ **이미지 다운로드** — 글에 포함된 이미지를 로컬에 저장하고 경로 자동 변환
- 📂 **카테고리별 폴더 정리** — 카테고리별로 폴더를 나누어 깔끔하게 정리
- ⏩ **이어받기 지원** — 중단된 곳에서 다시 시작 (`--skip-existing`)
- 🔒 **Rate Limiting** — 네이버 서버 차단을 방지하는 자동 딜레이

## 📦 설치

### 방법 1: pip 설치

```bash
pip install naverblog2obsidian
```

### 방법 2: 소스코드에서 설치

```bash
git clone https://github.com/kkw2030100/naverblog2obsidian.git
cd naverblog2obsidian
pip install -e .
```

### 방법 3: 직접 실행

```bash
git clone https://github.com/kkw2030100/naverblog2obsidian.git
cd naverblog2obsidian
pip install -r requirements.txt
python -m naverblog2obsidian
```

## 🚀 사용법

### 대화형 모드 (초보자 추천! 👍)

옵션 없이 실행하면 하나씩 친절하게 물어봅니다:

```bash
naverblog2obsidian
```

실행하면 이런 화면이 나옵니다:

```
==================================================
  📝 naverblog2obsidian
  네이버 블로그 → 옵시디언 마크다운 변환기
==================================================

📌 블로그 URL을 입력하세요: https://blog.naver.com/myblog

  ✅ 블로그 아이디: myblog

📂 카테고리 목록을 불러오는 중...

  번호  카테고리명
  ----------------------------------------
    1.  일상 이야기 (120개) [id:56]
    2.  여행 기록 (45개) [id:62]
    3.  맛집 리뷰 (89개) [id:4]

📋 가져올 카테고리 번호를 선택하세요
   (쉼표로 구분, 전체: Enter): 1,3

📁 저장 경로를 입력하세요 (기본: ./output): ~/my-obsidian-vault/블로그백업

🖼️  이미지도 다운로드할까요? (y/N): y

==================================================
  📋 설정 확인
  블로그: https://blog.naver.com/myblog
  카테고리: 일상 이야기, 맛집 리뷰
  저장 경로: /Users/me/my-obsidian-vault/블로그백업
  이미지 다운로드: 예
==================================================

시작할까요? (Y/n): y
```

### CLI 모드 (고급 사용자 / 자동화용)

#### 카테고리 목록 확인

```bash
naverblog2obsidian --blog https://blog.naver.com/myblog --list-categories
```

출력 예시:

```
📂 https://blog.naver.com/myblog 카테고리 목록:

  [ 56] 일상 이야기 (120개)
  [ 62] 여행 기록 (45개)
  [  4] 맛집 리뷰 (89개)

  전체 글 수: 254개
```

#### 전체 블로그 백업

```bash
naverblog2obsidian --blog https://blog.naver.com/myblog --dest ./output
```

#### 특정 카테고리만 백업

```bash
naverblog2obsidian --blog https://blog.naver.com/myblog --categories 56,4 --dest ./output
```

#### 이미지 포함 백업

```bash
naverblog2obsidian --blog https://blog.naver.com/myblog --dest ./output --download-images
```

#### 단일 글만 변환

```bash
naverblog2obsidian --url https://blog.naver.com/myblog/224228059529 --dest ./output
```

#### 이어받기 (중단 후 재시작)

```bash
naverblog2obsidian --blog https://blog.naver.com/myblog --dest ./output --skip-existing
```

## ⚙️ 전체 옵션

| 옵션 | 설명 | 기본값 |
|---|---|---|
| `--blog` | 블로그 URL | — |
| `--url` | 단일 글 URL | — |
| `--dest` | 저장 디렉토리 | `./output` |
| `--categories` | 카테고리 번호 (쉼표 구분) | 전체 |
| `--list-categories` | 카테고리 목록만 출력 | — |
| `--download-images` | 이미지 로컬 다운로드 | 안 함 |
| `--delay` | 요청 간 딜레이 (초) | 0.5 |
| `--skip-existing` | 기존 파일 건너뛰기 | 안 함 |
| `--verbose`, `-v` | 상세 로그 출력 | 안 함 |

## 📂 출력 구조

```
output/
├── 일상 이야기/
│   ├── 2024-03-24 오늘의 일기.md
│   ├── 2024-03-20 봄나들이.md
│   └── ...
├── 맛집 리뷰/
│   ├── 2024-03-15 강남 스시오마카세.md
│   ├── 2024-03-15 강남 스시오마카세/
│   │   └── images/
│   │       ├── img_001.jpg
│   │       └── img_002.jpg
│   └── ...
└── _uncategorized/
    └── ...
```

## 📄 변환된 파일 형식

각 마크다운 파일은 옵시디언 Properties(YAML frontmatter)를 포함합니다:

```markdown
---
title: "오늘의 일기"
date: 2024-03-24
source: "https://blog.naver.com/myblog/224228059529"
category: "일상 이야기"
tags: [일상, 봄, 나들이]
---

# 오늘의 일기

오늘은 날씨가 너무 좋아서 공원에 나갔습니다...
```

**포함되는 Properties:**
- `title` — 글 제목
- `date` — 작성일 (YYYY-MM-DD)
- `source` — 원본 네이버 블로그 URL
- `category` — 카테고리명
- `tags` — 해시태그 (글 하단의 태그 자동 추출)

## ❓ FAQ

### Q: 비공개 글도 가져올 수 있나요?
A: 아니요, 공개 글만 가져올 수 있습니다. 네이버 블로그 API는 공개 글만 접근 가능합니다.

### Q: 변환 중에 멈추면 어떻게 하나요?
A: `--skip-existing` 옵션을 사용하면 이미 변환된 파일은 건너뛰고 나머지만 처리합니다.

### Q: 네이버에서 차단당하지 않나요?
A: `--delay` 옵션으로 요청 간격을 조절할 수 있습니다. 기본값(0.5초)이면 대부분 괜찮지만, 글이 많은 경우 `--delay 1.0` 이상으로 올려주세요.

### Q: 이미지가 깨지면 어떻게 하나요?
A: `--download-images` 옵션을 사용하면 이미지를 로컬에 저장합니다. 네이버 서버의 이미지 URL은 시간이 지나면 접근이 안 될 수 있으므로, 이미지 다운로드를 권장합니다.

### Q: 옵시디언 볼트에 바로 저장할 수 있나요?
A: `--dest` 옵션에 옵시디언 볼트 경로를 지정하면 됩니다.
```bash
naverblog2obsidian --blog https://blog.naver.com/myblog --dest ~/my-vault/블로그백업
```

## 🔧 개발

```bash
git clone https://github.com/kkw2030100/naverblog2obsidian.git
cd naverblog2obsidian
pip install -e ".[dev]"
```

## 📜 라이선스

MIT License — 자유롭게 사용, 수정, 배포하실 수 있습니다.

## 🙏 기여

이슈, PR 환영합니다! 개선 아이디어가 있으면 GitHub Issues에 남겨주세요.

---

**Made with ❤️ by [Kim Kiwon](https://github.com/kkw2030100)**
