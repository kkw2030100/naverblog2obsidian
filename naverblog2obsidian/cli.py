"""CLI 엔트리포인트 — 대화형 + CLI 모드"""

import argparse
import os
import sys
from typing import Dict, List, Optional

from tqdm import tqdm

from .converter import convert_post, extract_images
from .crawler import NaverBlogCrawler
from .downloader import ImageDownloader, replace_image_urls
from .utils import ensure_dir, make_post_filename, sanitize_folder_name


def interactive_mode():
    """대화형 모드 — 옵션 없이 실행하면 하나씩 물어봄"""
    print()
    print("=" * 50)
    print("  📝 naverblog2obsidian")
    print("  네이버 블로그 → 옵시디언 마크다운 변환기")
    print("=" * 50)
    print()

    # 1. 블로그 URL 입력
    while True:
        blog_url = input("📌 블로그 URL을 입력하세요: ").strip()
        if not blog_url:
            print("  ⚠️  URL을 입력해주세요.")
            continue
        try:
            blog_id = NaverBlogCrawler.extract_blog_id(blog_url)
            break
        except ValueError as e:
            print(f"  ❌ {e}")

    print(f"\n  ✅ 블로그 아이디: {blog_id}")
    crawler = NaverBlogCrawler(blog_id)

    # 2. 카테고리 목록 표시
    print("\n📂 카테고리 목록을 불러오는 중...")
    categories = crawler.get_categories()

    if categories:
        print("\n  번호  카테고리명")
        print("  " + "-" * 40)
        cat_list = list(categories.items())
        for i, (cat_no, cat_name) in enumerate(cat_list, 1):
            count = crawler.get_category_post_count(cat_no)
            print(f"  {i:>3}.  {cat_name} ({count}개) [id:{cat_no}]")

        # 카테고리 선택
        print()
        selection = input(
            "📋 가져올 카테고리 번호를 선택하세요\n"
            "   (쉼표로 구분, 전체: Enter): "
        ).strip()

        if selection:
            selected_cats = {}
            try:
                indices = [int(x.strip()) for x in selection.split(",")]
                for idx in indices:
                    if 1 <= idx <= len(cat_list):
                        cat_no, cat_name = cat_list[idx - 1]
                        selected_cats[cat_no] = cat_name
                    else:
                        print(f"  ⚠️  {idx}번은 범위 밖입니다. 건너뜁니다.")
            except ValueError:
                print("  ⚠️  숫자를 입력해주세요. 전체 카테고리를 가져옵니다.")
                selected_cats = categories
        else:
            selected_cats = categories
    else:
        print("  ⚠️  카테고리를 찾을 수 없습니다. 전체 글을 가져옵니다.")
        selected_cats = {}

    # 3. 저장 경로
    print()
    dest = input("📁 저장 경로를 입력하세요 (기본: ./output): ").strip()
    if not dest:
        dest = "./output"

    # 4. 이미지 다운로드 여부
    print()
    img_input = input("🖼️  이미지도 다운로드할까요? (y/N): ").strip().lower()
    download_images = img_input in ("y", "yes", "ㅇ", "네")

    # 5. 확인
    print()
    print("=" * 50)
    print("  📋 설정 확인")
    print(f"  블로그: https://blog.naver.com/{blog_id}")
    if selected_cats:
        print(f"  카테고리: {', '.join(selected_cats.values())}")
    else:
        print("  카테고리: 전체")
    print(f"  저장 경로: {os.path.abspath(dest)}")
    print(f"  이미지 다운로드: {'예' if download_images else '아니오'}")
    print("=" * 50)
    print()
    confirm = input("시작할까요? (Y/n): ").strip().lower()
    if confirm in ("n", "no", "ㄴ", "아니"):
        print("취소되었습니다.")
        return

    # 실행
    run_export(
        blog_id=blog_id,
        categories=selected_cats if selected_cats else None,
        dest=dest,
        download_images=download_images,
        delay=0.5,
        skip_existing=False,
        verbose=True,
    )


def run_export(
    blog_id: str,
    categories: Optional[Dict[str, str]] = None,
    dest: str = "./output",
    download_images: bool = False,
    delay: float = 0.5,
    skip_existing: bool = False,
    verbose: bool = False,
    single_url: Optional[str] = None,
):
    """실제 내보내기 실행

    Args:
        blog_id: 블로그 아이디
        categories: {카테고리번호: 카테고리이름} (None이면 전체)
        dest: 저장 경로
        download_images: 이미지 다운로드 여부
        delay: 요청 간 딜레이
        skip_existing: 기존 파일 건너뛰기
        verbose: 상세 로그
        single_url: 단일 글 URL (있으면 이것만 처리)
    """
    crawler = NaverBlogCrawler(blog_id, delay=delay)
    img_downloader = ImageDownloader(delay=delay * 0.6) if download_images else None

    ensure_dir(dest)

    if single_url:
        _process_single_url(crawler, single_url, dest, categories, img_downloader, verbose)
        return

    # 카테고리별 또는 전체 글 목록 수집
    all_posts = []

    if categories:
        for cat_no, cat_name in categories.items():
            if verbose:
                print(f"\n📂 [{cat_name}] 글 목록 불러오는 중...")
            posts = crawler.get_post_list(category_no=cat_no)
            for post in posts:
                post["_category_name"] = cat_name
            all_posts.extend(posts)
            if verbose:
                print(f"  → {len(posts)}개 발견")
    else:
        if verbose:
            print("\n📂 전체 글 목록 불러오는 중...")
        all_posts = crawler.get_post_list()
        # 카테고리 이름 매핑
        all_categories = crawler.get_categories()
        for post in all_posts:
            cat_no = post.get("categoryNo", "")
            post["_category_name"] = all_categories.get(cat_no, "_uncategorized")

    if not all_posts:
        print("❌ 가져올 글이 없습니다.")
        return

    print(f"\n📝 총 {len(all_posts)}개 글을 변환합니다...\n")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for post in tqdm(all_posts, desc="변환 중", unit="글"):
        try:
            title = post["title"]
            date = post["addDate"]
            log_no = post["logNo"]
            cat_name = post.get("_category_name", "_uncategorized")

            # 폴더 생성
            folder_name = sanitize_folder_name(cat_name)
            post_dir = os.path.join(dest, folder_name)
            ensure_dir(post_dir)

            # 파일명
            filename = make_post_filename(date, title)
            filepath = os.path.join(post_dir, filename)

            # 기존 파일 건너뛰기
            if skip_existing and os.path.exists(filepath):
                skip_count += 1
                continue

            # 본문 크롤링
            fetched_title, fetched_date, html_soup = crawler.get_post_html(log_no)
            if not fetched_date:
                fetched_date = date

            # 변환
            url = f"https://blog.naver.com/{blog_id}/{log_no}"
            markdown = convert_post(
                title=fetched_title or title,
                date=fetched_date,
                html_soup=html_soup,
                url=url,
                category=cat_name,
            )

            # 이미지 다운로드
            if img_downloader and html_soup:
                image_urls = extract_images(html_soup)
                if image_urls:
                    # 이미지 폴더: 글 제목과 동일한 폴더 아래 images/
                    img_folder_name = sanitize_folder_name(fetched_title or title)
                    img_dest = os.path.join(post_dir, img_folder_name, "images")
                    url_map = img_downloader.download_images(
                        image_urls, img_dest, verbose=verbose
                    )
                    # 마크다운 내 URL 치환
                    rel_img_folder = f"{img_folder_name}/images"
                    markdown = replace_image_urls(markdown, url_map, rel_img_folder)

            # 저장
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown)

            success_count += 1

        except Exception as e:
            fail_count += 1
            if verbose:
                tqdm.write(f"  ❌ 실패: {post.get('title', '?')} — {e}")

    # 결과 요약
    print()
    print("=" * 50)
    print("  ✅ 변환 완료!")
    print(f"  성공: {success_count}개")
    if skip_count:
        print(f"  건너뜀: {skip_count}개")
    if fail_count:
        print(f"  실패: {fail_count}개")
    print(f"  저장 위치: {os.path.abspath(dest)}")
    print("=" * 50)


def _process_single_url(crawler, url, dest, categories, img_downloader, verbose):
    """단일 URL 처리"""
    blog_id, log_no = NaverBlogCrawler.extract_post_info(url)
    crawler_for_post = NaverBlogCrawler(blog_id, delay=crawler.delay)

    title, date, html_soup = crawler_for_post.get_post_html(log_no)

    markdown = convert_post(
        title=title,
        date=date,
        html_soup=html_soup,
        url=url,
        category="",
    )

    if img_downloader and html_soup:
        image_urls = extract_images(html_soup)
        if image_urls:
            img_folder_name = sanitize_folder_name(title)
            img_dest = os.path.join(dest, img_folder_name, "images")
            url_map = img_downloader.download_images(image_urls, img_dest, verbose=verbose)
            markdown = replace_image_urls(markdown, url_map, f"{img_folder_name}/images")

    filename = make_post_filename(date, title)
    filepath = os.path.join(dest, filename)
    ensure_dir(dest)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"\n✅ 저장 완료: {filepath}")


def main():
    """메인 엔트리포인트"""
    # 인자가 없으면 대화형 모드
    if len(sys.argv) == 1:
        interactive_mode()
        return

    parser = argparse.ArgumentParser(
        prog="naverblog2obsidian",
        description="네이버 블로그를 옵시디언 마크다운으로 변환합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 대화형 모드 (옵션 없이 실행)
  naverblog2obsidian

  # 카테고리 목록 확인
  naverblog2obsidian --blog https://blog.naver.com/myblog --list-categories

  # 전체 블로그 백업
  naverblog2obsidian --blog https://blog.naver.com/myblog --dest ./output

  # 특정 카테고리만
  naverblog2obsidian --blog https://blog.naver.com/myblog --categories 56,4 --dest ./output

  # 단일 글 변환
  naverblog2obsidian --url https://blog.naver.com/myblog/123456789 --dest ./output

  # 이미지 포함 + 이어받기
  naverblog2obsidian --blog https://blog.naver.com/myblog --dest ./output --download-images --skip-existing
        """,
    )

    parser.add_argument("--blog", help="블로그 URL (예: https://blog.naver.com/myblog)")
    parser.add_argument("--url", help="단일 글 URL")
    parser.add_argument("--dest", default="./output", help="저장 디렉토리 (기본: ./output)")
    parser.add_argument(
        "--categories", help="카테고리 번호 (쉼표 구분, 예: 56,4)"
    )
    parser.add_argument(
        "--list-categories", action="store_true", help="카테고리 목록만 출력"
    )
    parser.add_argument(
        "--download-images", action="store_true", help="이미지 로컬 다운로드"
    )
    parser.add_argument(
        "--delay", type=float, default=0.5, help="요청 간 딜레이 초 (기본: 0.5)"
    )
    parser.add_argument(
        "--skip-existing", action="store_true", help="기존 파일 건너뛰기 (이어받기)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그 출력")

    args = parser.parse_args()

    # 블로그 URL 또는 단일 URL 필수
    if not args.blog and not args.url:
        parser.error("--blog 또는 --url 중 하나를 지정해주세요.")

    # 단일 글 처리
    if args.url:
        blog_id, _ = NaverBlogCrawler.extract_post_info(args.url)
        run_export(
            blog_id=blog_id,
            dest=args.dest,
            download_images=args.download_images,
            delay=args.delay,
            verbose=args.verbose,
            single_url=args.url,
        )
        return

    blog_id = NaverBlogCrawler.extract_blog_id(args.blog)
    crawler = NaverBlogCrawler(blog_id, delay=args.delay)

    # 카테고리 목록 출력
    if args.list_categories:
        print(f"\n📂 {args.blog} 카테고리 목록:\n")
        categories = crawler.get_categories()
        if not categories:
            print("  카테고리를 찾을 수 없습니다.")
            return
        for cat_no, cat_name in categories.items():
            count = crawler.get_category_post_count(cat_no)
            print(f"  [{cat_no:>3}] {cat_name} ({count}개)")
        total = crawler.get_total_post_count()
        print(f"\n  전체 글 수: {total}개")
        return

    # 카테고리 필터링
    selected_categories = None
    if args.categories:
        all_cats = crawler.get_categories()
        selected_categories = {}
        for cat_no in args.categories.split(","):
            cat_no = cat_no.strip()
            if cat_no in all_cats:
                selected_categories[cat_no] = all_cats[cat_no]
            else:
                print(f"  ⚠️  카테고리 {cat_no}을 찾을 수 없습니다. 건너뜁니다.")

    # 실행
    run_export(
        blog_id=blog_id,
        categories=selected_categories,
        dest=args.dest,
        download_images=args.download_images,
        delay=args.delay,
        skip_existing=args.skip_existing,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
