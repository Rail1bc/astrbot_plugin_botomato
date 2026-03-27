from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any, Dict

from rain_api.rain_tomato_api import RainTomatoAPI


@dataclass
class BookInfo:

    book_id: str    # 书籍 ID
    book_name: str  # 书名
    alias_name: str # 别名
    original_book_name: str # 原书名
    author: str     # 作者
    abstract: str = ""  # 简介
    word_number: Optional[int] = None   # 字数
    serial_count: Optional[int] = None  # 章节数
    read_cnt_text: str = ""  # 在读人数
    score: Optional[float] = None   # 评分
    raw: Dict[str, Any] = field(default_factory=dict)   # 原始数据

    @classmethod
    def from_dict(cls, data: Dict[str: Any]) -> "BookInfo":
        """从 API 返回的字典构造 BookInfo，尽量容错并解析常见格式。"""
        if data is None:
            raise ValueError("data is required")

        book_id = data.get("book_id")
        book_name = data.get("book_name")
        alias_name = data.get("alias_name") or data.get("book_flight_alias_name")
        original_book_name = data.get("original_book_name")
        author = data.get("author")
        abstract = data.get("abstract")
        word_number = data.get("word_number")
        serial_count = data.get("serial_count")
        read_cnt_text = data.get("read_cnt_text")
        score = data.get("score")

        return cls(
            book_id=book_id,
            book_name=book_name,
            alias_name=alias_name,
            original_book_name=original_book_name,
            author=author,
            abstract=abstract,
            word_number=word_number,
            serial_count=serial_count,
            read_cnt_text=read_cnt_text,
            score=score,
            raw=data,
        )

@dataclass
class ChapterInfo:
    item_id: str
    title: str
    volume_name: str

    @classmethod
    def from_api_dict(cls, data: dict) -> "ChapterInfo":
        item_id = data.get("item_id")
        title = data.get("title")
        volume_name = data.get("volume_name")
        return cls(
            item_id=item_id,
            title=title,
            volume_name=volume_name,
            raw=data,
        )

class Book:
    """Book 持有 BookInfo；未来可挂载章节、进度、缓存等行为。

    当前实现为一个轻量包装：提供访问、序列化等实用方法。
    """

    def __init__(self, info: BookInfo):
        self.info = info
        self.chapter_list: Optional[list[ChapterInfo]] = None

    def __repr__(self) -> str:
        return f"<Book id={self.info.book_id!r} name={self.info.book_name!r} author={self.info.author!r}>"

    @classmethod
    def from_api_dict(cls, data: Dict[str, Any]) -> "Book":
        """从 书籍数据 构造 Book """
        info = BookInfo.from_dict(data)
        return cls(info)

    @classmethod
    def book_list_from_api_dict(cls, data_list: Optional[list[dict[str, Any]]]) -> list["Book"]:
        """从 书籍数据列表 构造 Book 列表"""
        if not data_list:
            return []
        book_list: list["Book"] = []
        for data in data_list:
            book_list.append(cls.from_api_dict(data))
        return book_list

    def book_info_to_str(self) -> str:
        """
        将书籍信息反序列化为字符串
        适合在聊天中展示
        """
        parts = []
        parts.append(f"《{self.info.book_name}》")
        parts.append(f"作者：{self.info.author}")
        parts.append(f"评分：{self.info.score}")
        parts.append(f"在读：{self.info.read_cnt_text}")
        parts.append(f"书籍id:{self.info.book_id}")
        parts.append(self.info.abstract.strip())
        return "\n* ".join(parts) if parts else repr(self)

    def _get_chapter_context(self, api: RainTomatoAPI, index: int) -> dict:
        """获取第 n 章正文"""


    def update_chapter_list(self, api: RainTomatoAPI):
        """更新书籍章节列表"""
        chapter_list:list[ChapterInfo] = []
        for data in api.toc(self.info.book_id):
            chapter_list.append(ChapterInfo.from_api_dict(data))
        self.chapter_list = chapter_list


    def update_book_info(self, api: RainTomatoAPI):
        """更新书籍信息"""
        data = api.book_info(self.info.book_id)
        if data:
            self.info = BookInfo.from_dict(data)

    def update(self, api: RainTomatoAPI):
        self.update_book_info(api)
        self.update_chapter_list(api)
