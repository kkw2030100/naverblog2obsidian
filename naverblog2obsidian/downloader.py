"""이미지 다운로드 모듈"""

import os
import re
import time
from typing import Dict
from urllib.parse import urlparse

import requests


class ImageDownloader:
    """네이버 블로그 이미지 다운로더"""

    def __init__(self, delay: float = 0.3):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://blog.naver.com/",
        })

    def download_images(
        self,
        image_urls: list,
        dest_dir: str,
        verbose: bool = False,
    ) -> Dict[str, str]:
        """이미지 URL 리스트를 다운로드하고 로컬 경로 매핑 반환

        Args:
            image_urls: 이미지 URL 리스트
            dest_dir: 이미지 저장 디렉토리
            verbose: 상세 로그 출력

        Returns:
            {원본URL: 로컬상대경로} 딕셔너리
        """
        os.makedirs(dest_dir, exist_ok=True)
        url_map = {}

        for i, url in enumerate(image_urls):
            filename = self._url_to_filename(url, i)
            filepath = os.path.join(dest_dir, filename)

            if os.path.exists(filepath):
                if verbose:
                    print(f"  ⏭️  이미지 이미 존재: {filename}")
                url_map[url] = filename
                continue

            try:
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()

                with open(filepath, "wb") as f:
                    f.write(resp.content)

                url_map[url] = filename
                if verbose:
                    print(f"  📥 이미지 다운로드: {filename}")

                if self.delay > 0:
                    time.sleep(self.delay)

            except Exception as e:
                if verbose:
                    print(f"  ❌ 이미지 다운로드 실패: {url} ({e})")
                # 실패 시 원본 URL 유지
                url_map[url] = url

        return url_map

    @staticmethod
    def _url_to_filename(url: str, index: int) -> str:
        """URL에서 파일명 생성"""
        parsed = urlparse(url)
        path = parsed.path

        # 확장자 추출
        ext_match = re.search(r"\.(jpe?g|png|gif|webp|bmp|svg)", path, re.IGNORECASE)
        ext = ext_match.group(0) if ext_match else ".jpg"

        return f"img_{index + 1:03d}{ext}"


def replace_image_urls(markdown: str, url_map: Dict[str, str], images_folder: str = "images") -> str:
    """마크다운 내 이미지 URL을 로컬 경로로 치환

    Args:
        markdown: 마크다운 텍스트
        url_map: {원본URL: 로컬파일명} 딕셔너리
        images_folder: 이미지 폴더명

    Returns:
        치환된 마크다운 텍스트
    """
    for original_url, local_name in url_map.items():
        if local_name.startswith("http"):
            continue  # 다운로드 실패한 경우 원본 유지
        local_path = f"{images_folder}/{local_name}"
        markdown = markdown.replace(original_url, local_path)

    return markdown
