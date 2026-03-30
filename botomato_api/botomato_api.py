import asyncio
import logging
from typing import List, Optional, Any, Dict
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://botomato.raila.cn"

class BotomatoAPI:
    """
    Bot tomato API
    bot专用的番茄小说API，有严格限速，请勿滥用！
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 10,
        max_retries: int = 2,
        backoff: float = 0.3,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        """
        初始化API。

        :param base_url: 基地址
        :param timeout: 请求超时时间（秒）
        :param max_retries: 最大重试次数（不包含首次）
        :param backoff: 重试退避基数（sleep = backoff * attempt）
        :param session: 可选的aiohttp会话，若不提供则内部创建
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self._session = session
        self._own_session = session is None

    _instance = None

    @classmethod
    async def get_instance(cls, **kwargs):
        """获取全局单例实例（首次调用时初始化）"""
        if cls._instance is None:
            cls._instance = cls(**kwargs)
            # 注意：如果使用异步上下文管理器，需要手动调用 __aenter__ 初始化会话
            await cls._instance.__aenter__()
        return cls._instance

    @classmethod
    async def destroy_instance(cls):
        """销毁单例实例，关闭会话并重置状态"""
        if cls._instance is not None:
            await cls._instance.close()  # 调用实例的close方法关闭会话
            cls._instance = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取当前会话，若未创建则创建"""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "botomato-bot-client/1.0",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                }
            )
        return self._session

    async def close(self):
        """关闭会话（如果由内部创建）"""
        if self._own_session and self._session:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()

    async def _get(self, path: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        params = params.copy()
        url = f"{self.base_url}/{path}?{urlencode(params)}"

        session = await self._get_session()
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        last_err = None

        for attempt in range(self.max_retries + 1):  # 尝试次数 = max_retries+1
            try:
                async with session.get(url, timeout=timeout) as resp:
                    resp.raise_for_status()
                    text = await resp.text()
                    if not text or text.strip() == "null":
                        raise TypeError("响应为空或null")
                    data = await resp.json()
                    if data.get("message") != "SUCCESS":
                        raise ValueError(f"业务状态异常, message:{data.get('message')}")
                    return data

            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
                last_err = e
                logger.debug("请求失败（尝试 %d/%d）: %s", attempt + 1, self.max_retries + 1, e)
                if attempt < self.max_retries:  # 还有重试机会
                    await asyncio.sleep(self.backoff * (attempt + 1))
                else:
                    break  # 重试耗尽，退出循环

        # 所有尝试均失败
        logger.warning("已超过最大重试次数:\n%s", last_err)
        raise Exception(f"超过最大重试次数:\n{last_err}") from last_err

    async def search(self, keywords: str, page: int = 0) -> List[Dict[str, Any]]:
        """
        搜索书籍。

        :param keywords: 搜索关键词
        :param page: 页码
        :return: 书籍列表
        """
        params = {"query": keywords, "page": page}
        try:
            data = await self._get("search",params)
        except Exception as e:
            raise Exception(f"搜索请求失败,{e}") from e
        search_tabs = data.get("search_tabs", [])
        # 找到 tab_type 为 3 或 '3' 的 tab
        target_tab = next(
            (tab for tab in search_tabs if tab.get("tab_type") in (3, "3")),
            None,
        )
        book_list = []
        for cell in target_tab.get("data", []):
            book_data = cell.get("book_data")
            if book_data and isinstance(book_data, list) and len(book_data) > 0:
                book_list.append(book_data[0])
        return book_list



    async def book_info(self, bookid: str) -> Optional[Dict[str, Any]]:
        """
        获取书籍详细信息。

        :param bookid: 书籍ID
        :return: 书籍信息字典，失败返回None
        """
        params = {"book_id": bookid}
        try:
            data = await self._get("detail", params)
        except Exception as e:
            raise Exception(f"获取书籍信息请求失败,{e}") from e
        return data.get("data") if data else None

    async def toc(self, bookid: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取目录（章节列表）。

        :param bookid: 书籍ID
        :return: 目录列表，失败返回None
        """
        params = {"book_id": bookid}
        try:
            data = await self._get("catalog", params)
        except Exception as e:
            raise Exception(f"获取目录请求失败,{e}") from e
        if data:
            return data.get("data", {}).get("item_data_list")
        return None

    async def chapter(self, itemid: str) -> Optional[Dict[str, Any]]:
        """
        获取章节内容。

        :param itemid: 章节ID
        :return: 章节内容字典，失败返回None
        """
        params = {"item_id": itemid}
        try:
            data = await self._get("content",params)
        except Exception as e:
            raise Exception(f"获取章节内容请求失败,{e}") from e
        return data.get("data") if data else None