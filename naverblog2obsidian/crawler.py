"""네이버 블로그 크롤링 모듈"""

import json
import re
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup


class NaverBlogCrawler:
    """네이버 블로그 크롤러"""

    BASE_URL = "https://blog.naver.com"
    POST_LIST_API = f"{BASE_URL}/PostTitleListAsync.naver"
    POST_VIEW_URL = f"{BASE_URL}/PostView.naver"

    def __init__(self, blog_id: str, delay: float = 0.5):
        """
        Args:
            blog_id: 블로그 아이디 (예: 'irichgo')
            delay: 요청 간 딜레이 (초). 네이버 차단 방지용.
        """
        self.blog_id = blog_id
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{self.BASE_URL}/{blog_id}",
        })

    def _wait(self):
        """요청 간 딜레이"""
        if self.delay > 0:
            time.sleep(self.delay)

    @staticmethod
    def extract_blog_id(url: str) -> str:
        """블로그 URL에서 블로그 아이디 추출

        Args:
            url: 블로그 URL (예: 'https://blog.naver.com/irichgo')

        Returns:
            블로그 아이디 문자열
        """
        url = url.rstrip("/")
        match = re.search(r"blog\.naver\.com/([^/?#]+)", url)
        if match:
            return match.group(1)
        raise ValueError(f"올바른 네이버 블로그 URL이 아닙니다: {url}")

    @staticmethod
    def extract_post_info(url: str) -> Tuple[str, str]:
        """글 URL에서 (blog_id, logNo) 추출

        Args:
            url: 글 URL

        Returns:
            (blog_id, logNo) 튜플
        """
        # https://blog.naver.com/irichgo/224228059529
        match = re.search(r"blog\.naver\.com/([^/?#]+)/(\d+)", url)
        if match:
            return match.group(1), match.group(2)

        # https://blog.naver.com/PostView.naver?blogId=irichgo&logNo=224228059529
        match = re.search(r"blogId=([^&]+).*logNo=(\d+)", url)
        if match:
            return match.group(1), match.group(2)

        raise ValueError(f"올바른 네이버 블로그 글 URL이 아닙니다: {url}")

    def get_categories(self) -> Dict[str, str]:
        """블로그의 카테고리 목록 조회

        Returns:
            {카테고리번호: 카테고리이름} 딕셔너리
        """
        url = f"{self.BASE_URL}/PostList.naver?blogId={self.blog_id}"
        resp = self.session.get(url)
        resp.raise_for_status()

        categories = {}
        # 메뉴 영역에서 카테고리 추출
        for match in re.finditer(
            r'categoryNo=(\d+)[^"]*from=menu[^>]*class="[^"]*itemfont[^"]*"[^>]*>([^<]+)',
            resp.text,
        ):
            cat_no, cat_name = match.group(1), match.group(2).strip()
            categories[cat_no] = cat_name

        # 글 목록에서도 추가 카테고리 수집
        for match in re.finditer(
            r'categoryNo=(\d+)[^"]*from=postList[^>]*>([^<]+)',
            resp.text,
        ):
            cat_no, cat_name = match.group(1), match.group(2).strip()
            if cat_no not in categories:
                categories[cat_no] = cat_name

        self._wait()
        return categories

    def get_category_post_count(self, category_no: str) -> int:
        """특정 카테고리의 글 수 조회"""
        params = {
            "blogId": self.blog_id,
            "currentPage": 1,
            "countPerPage": 1,
            "categoryNo": category_no,
        }
        resp = self.session.get(self.POST_LIST_API, params=params)
        resp.raise_for_status()
        data = json.loads(resp.text.replace("\\", "\\\\"))
        self._wait()
        return int(data.get("totalCount", 0))

    def get_total_post_count(self) -> int:
        """전체 글 수 조회"""
        params = {
            "blogId": self.blog_id,
            "currentPage": 1,
            "countPerPage": 1,
        }
        resp = self.session.get(self.POST_LIST_API, params=params)
        resp.raise_for_status()
        data = json.loads(resp.text.replace("\\", "\\\\"))
        self._wait()
        return int(data.get("totalCount", 0))

    def get_post_list(
        self,
        category_no: Optional[str] = None,
        count_per_page: int = 30,
    ) -> List[Dict]:
        """글 목록 전체 가져오기

        Args:
            category_no: 카테고리 번호 (None이면 전체)
            count_per_page: 페이지당 글 수

        Returns:
            글 정보 딕셔너리 리스트
        """
        all_posts = []
        current_page = 1
        total_count = None

        while total_count is None or len(all_posts) < total_count:
            params = {
                "blogId": self.blog_id,
                "currentPage": current_page,
                "countPerPage": count_per_page,
            }
            if category_no:
                params["categoryNo"] = category_no

            resp = self.session.get(self.POST_LIST_API, params=params)
            resp.raise_for_status()

            data = json.loads(resp.text.replace("\\", "\\\\"))
            total_count = int(data.get("totalCount", 0))
            posts = data.get("postList", [])

            if not posts:
                break

            for post in posts:
                all_posts.append({
                    "logNo": post["logNo"],
                    "title": unquote(post.get("title", "").replace("+", " ")),
                    "categoryNo": post.get("categoryNo", ""),
                    "parentCategoryNo": post.get("parentCategoryNo", ""),
                    "addDate": post.get("addDate", "").strip(),
                    "commentCount": post.get("commentCount", "0"),
                })

            current_page += 1
            self._wait()

        return all_posts

    def get_post_html(self, log_no: str) -> Tuple[str, str, BeautifulSoup]:
        """개별 글의 HTML 본문 가져오기

        Args:
            log_no: 글 번호

        Returns:
            (제목, 작성일, 본문 BeautifulSoup) 튜플
        """
        url = f"{self.POST_VIEW_URL}?blogId={self.blog_id}&logNo={log_no}"
        resp = self.session.get(url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # 제목 추출
        title_tag = soup.find("title")
        title = title_tag.text.strip() if title_tag else "Untitled"
        # " : 네이버 블로그" 접미사 제거
        title = re.sub(r"\s*:\s*네이버\s*블로그\s*$", "", title)

        # 작성일 추출
        date_tag = soup.find("span", class_="se_publishDate") or soup.find(
            "p", class_="blog_date"
        )
        date_str = date_tag.text.strip() if date_tag else ""

        # 본문 추출
        post_view = soup.find("div", attrs={"id": f"post-view{log_no}"})
        if not post_view:
            # 대안: se-main-container
            post_view = soup.find("div", class_="se-main-container")
        if not post_view:
            post_view = soup.find("div", id="postViewArea")

        self._wait()
        return title, date_str, post_view
