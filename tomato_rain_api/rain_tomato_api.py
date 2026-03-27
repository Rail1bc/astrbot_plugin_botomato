from typing import List

import requests
import time
import logging
from urllib.parse import urlencode

from tomato_rain_api.book import Book

logger = logging.getLogger(__name__)

class RainTomatoAPI:
    # 默认 base 地址
    DEFAULT_BASE = "https://v3.rain.ink/fanqie/"

    def __init__(self, apikey: str, base_url: str = None, timeout: int = 10, max_retries: int = 2, backoff: float = 0.3):
        """初始化api。
        参数:
            apikey: 访问网关的 API key。
            base_url: 书源基地址（覆盖默认 DEFAULT_BASE）。
            timeout: 请求超时时间（秒）。
            max_retries: 发生请求异常时的最大重试次数（不包含首次尝试）。
            backoff: 重试回退基数，用于指数退避（sleep = backoff * attempt）。
        """
        if not apikey or not base_url:
            raise ValueError("没有apikey或书源地址")
        self.apikey = apikey
        self.base_url = base_url or RainTomatoAPI.DEFAULT_BASE
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "tomato-rain-client/1.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        })

    # 将搜索 / 书籍信息 / 目录 / 章节作为类方法
    def search(self, keywords: str, page: int = 0) -> List[Book]:
        params = {'type': 1, 'keywords': keywords, 'page': page}
        search_result = self._get(params)
        data_list = self._get_search_item(search_result)
        return Book.book_list_from_api_dict(data_list)


    def book_info(self, bookid: str):
        params = {'type': 2, 'bookid': bookid}
        return self._get(params).get("data")

    def toc(self, bookid: str):
        params = {'type': 3, 'bookid': bookid}
        return self._get(params).get("data").get("item_data_list")

    def chapter(self, itemid: str, tone: dict = None):
        params = {'type': 4, 'itemid': itemid}
        if tone and isinstance(tone, dict):
            params.update(tone)
        return self._get(params).get("data")

    def _get(self, params: dict) -> dict:
        """内部通用 GET 请求构建与执行函数。

        行为说明：
            - 支持重复尝试请求（基于 max_retries）并进行指数退避。
            - 若响应 body 为空或为字符串 'null'，返回 None；若响应不是 JSON，返回原始文本。
        参数:
            params: 要附加到查询字符串的参数字典。

        返回值:
            - 成功时返回解析后的 JSON dict；
            - 对于显式的空/ null 响应返回 None；
            - 在超出重试次数并发生请求异常时抛出最后一次的 RequestException。
        """
        params = params.copy()
        params['apikey'] = self.apikey
        base = self.base_url
        # 构建 URL：如果 base 已经包含 '?'，则使用 '&' 连接，否则使用 '?'
        url = base
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}{urlencode(params)}"
        last_err = None
        # total attempts = 1 + max_retries
        for attempt in range(1, self.max_retries + 2):
            try:
                resp = self.session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                # 响应可能为空或为字符串 'null'，在这些情况下统一返回空 dict
                if not resp.text or resp.text.strip() == 'null':
                    return {}
                try:
                    # 优先尝试解析为 JSON
                    return resp.json()
                except ValueError:
                    # 如果不是 JSON，则返回原始文本
                    return {"text": resp.text}
            except requests.RequestException as e:
                # 记录最后一个错误并在下一次重试前等待
                last_err = e
                logger.debug('Request failed attempt %s: %s', attempt, e)
                time.sleep(self.backoff * attempt)
        # 超出重试次数后抛出最后一次捕获的异常
        raise last_err


    def _get_search_item(self, data: dict) -> list:
        """
        从搜索结果提取出数据块列表
        失败返回空列表
        """

        if not data:
            logger.warning("搜索失败")
            return []
        data = data.get("search_tabs")
        if not isinstance(data, list):
            logger.warning("search_tabs 不是期望的列表: %r", data)
            return []
        data = next((tab for tab in data if tab.get('tab_type') in (3, '3')), None)
        if data is []:
            logger.warning("没有找到 书籍 的 tab")
            return []
        data = data.get("data")
        book_list = []
        for cell in data:
            book_list.append(cell.get("book_data")[0])
        return book_list
