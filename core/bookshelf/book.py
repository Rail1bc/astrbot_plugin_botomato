from dataclasses import dataclass, field
from typing import Optional, Any, Dict

from ...rain_api.rain_tomato_api import RainTomatoAPI


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
    def from_dict(cls, data: Dict[str, Any]) -> "BookInfo":
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
    version: str
    title: str
    volume_name: str

    @classmethod
    def from_api_dict(cls, data: dict) -> "ChapterInfo":
        item_id = data.get("item_id")
        version = data.get("version")
        title = data.get("title")
        volume_name = data.get("volume_name")
        return cls(
            item_id=item_id,
            version=version,
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

    # -------- 工厂方法 --------

    @classmethod
    def book_from_dict(cls, data: Dict[str, Any]) -> "Book":
        """从 json数据 构造 Book """
        info = BookInfo.from_dict(data)
        return cls(info)

    @classmethod
    def book_list_from_dict(cls, data_list: Optional[list[dict[str, Any]]]) -> list["Book"]:
        """从 书籍数据列表 构造 Book列表"""
        book_list: list["Book"] = []
        for data in data_list:
            book_list.append(cls.book_from_dict(data))
        return book_list

    @classmethod
    async def book_from_bookid(cls, bookid: str) -> "Book":
        """通过 书籍id 获取 json数据 以构造 Book"""
        api = await RainTomatoAPI.get_instance()
        if (api is None) or (api.enable is False):
            raise Exception("api失效，无法更新、获取新的书籍信息。")
        book_data = await api.book_info(bookid)
        if not book_data:
            raise Exception(f"未找到ID为 {bookid} 的书籍,书籍ID是真实的吗？")
        return cls(BookInfo.from_dict(book_data))

    # ----------- 实例方法 -----------
    # ----------- 更新 ------------

    async def update(self):
        """更新书籍数据"""
        await self.update_book_info()
        await self.update_chapter_list()

    async def update_book_info(self):
        """更新书籍信息"""
        api = await RainTomatoAPI.get_instance()
        data = await api.book_info(self.info.book_id)
        if data:
            self.info = BookInfo.from_dict(data)

    async def update_chapter_list(self):
        """通过 bookid 获取最新章节数据 并更新书籍章节列表"""
        api = await RainTomatoAPI.get_instance()
        item_list = await api.toc(self.info.book_id)
        chapter_list:list[ChapterInfo] = []
        for data in item_list:
            chapter_list.append(ChapterInfo.from_api_dict(data))
        self.chapter_list = chapter_list

    # ---------- 实例方法 ---------------

    def book_info_to_str(self) -> str:
        """
        将书籍信息 反序列化为 适合在聊天中展示的字符串
        """
        parts = []
        parts.append(f"《{self.info.book_name}》")
        parts.append(f"作者：{self.info.author}")
        parts.append(f"评分：{self.info.score}")
        parts.append(f"在读：{self.info.read_cnt_text}")
        parts.append(f"书籍id:{self.info.book_id}")
        parts.append(self.info.abstract.strip())
        return "\n* ".join(parts) if parts else repr(self)




