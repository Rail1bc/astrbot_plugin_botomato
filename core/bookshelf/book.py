from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List

from ...botomato_api.botomato_api import BotomatoAPI

# ------------ 数据类 ------------
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
    @classmethod
    def from_dict_list(cls, data: List[dict]) -> List["BookInfo"]:
        return [BookInfo.from_dict(data) for data in data]

@dataclass
class ChapterInfo:
    item_id: str
    version: str
    title: str
    volume_name: str
    raw: Dict[str, Any] = field(default_factory=dict)   # 原始数据

    @classmethod
    def from_dict(cls, data: dict) -> "ChapterInfo":
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
    @classmethod
    def from_dict_list(cls, data: List[dict]) -> List["ChapterInfo"]:
        return [ChapterInfo.from_dict(data) for data in data]

@dataclass
class ContentInfo:
    item_id: str
    version: str
    title: str
    content: str
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api_dict(cls, chapter: ChapterInfo, data: dict,) -> "ContentInfo":
        title = data.get("title")
        content = data.get("content")
        return cls(
            item_id=chapter.item_id,
            version=chapter.version,
            title=title,
            content=content,
            raw=data,
        )
    @classmethod
    def from_db_dict(cls, data: dict) -> "ContentInfo":
        item_id = data.get("item_id")
        version = data.get("version")
        title = data.get("title")
        content = data.get("content")
        suffix = "\\n 为保证服务质量，免费用户请不要下书！或前往网站赞助后刷新隐藏该提示(赞助用户一天可下载一万章)"
        if content.endswith(suffix):
            content = content[:-len(suffix)]
        content = content.replace("</p>", "\n")
        return cls(
            item_id=item_id,
            version=version,
            title=title,
            content=content,
            raw=data,
        )

    @classmethod
    def from_dict_list(cls, data: List[dict]) -> List["ContentInfo"]:
        return [ContentInfo.from_db_dict(data) for data in data]

# ------------ 书籍类 ------------

class Book:
    """
    Book 持有 BookInfo。
    可能持有 List[ChapterInfo] 和 List[ContentInfo],
    当前实现为一个轻量包装：提供基础行为方法
    """

    def __init__(self, info: BookInfo):
        self.info = info
        self.chapter_list: Optional[List[ChapterInfo]] = []
        self.content_list: Optional[List[ContentInfo]] = []

    def __repr__(self) -> str:
        return f"<Book id={self.info.book_id!r} name={self.info.book_name!r} author={self.info.author!r}>"

    # -------- 工厂方法 --------
    # -------- 通过数据构造 --------
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Book":
        """通过数据构造 Book """
        return cls(BookInfo.from_dict(data))

    @classmethod
    def list_from_dict(cls, data_list: Optional[List[dict[str, Any]]]) -> List["Book"]:
        """通过数据构造 List[Book]"""
        return [cls(info) for info in BookInfo.from_dict_list(data_list)]

    # -------- 通过网络拉取 -----------
    @classmethod
    async def from_bookid(cls, book_id: str) -> "Book":
        """通过book_id从网络拉取数据构造 Book"""
        api = await BotomatoAPI.get_instance()
        try:
            book_data = await api.book_info(book_id)
        except Exception as e:
            raise TypeError(f"构造书籍失败:\n{e}") from e
        return cls(BookInfo.from_dict(book_data))

    # ----------- 实例方法 -----------
    # ----------- 更新 ------------

    async def update(self):
        """更新书籍数据"""
        result = [await self._update_book_info(),
                  await self._update_chapter_list(),
                  await self._update_content_list()]
        return "\n".join(result)

    async def _update_book_info(self) -> str:
        """更新书籍信息"""
        api = await BotomatoAPI.get_instance()
        try:
            data = await api.book_info(self.info.book_id)
        except Exception as e:
            raise TypeError(f"拉取书籍基础信息失败:\n{e}") from e
        self.info = BookInfo.from_dict(data)
        return f"《{self.info.book_name}》基础信息拉取成功"

    async def _update_chapter_list(self) -> str:
        """通过 bookid 获取最新章节数据 并更新书籍章节列表"""
        api = await BotomatoAPI.get_instance()
        try:
            item_list = await api.toc(self.info.book_id)
        except Exception as e:
            self.chapter_list = []
            return f"拉取《{self.info.book_name}》章节列表失败:\n{e}"
        self.chapter_list = ChapterInfo.from_dict_list(item_list)
        return f"《{self.info.book_name}》章节列表拉取成功"

    async def update_chapter_list(self) -> bool:
        """通过 bookid 获取最新章节数据 并更新书籍章节列表"""
        api = await BotomatoAPI.get_instance()
        try:
            item_list = await api.toc(self.info.book_id)
        except Exception as e:
            return False
        self.chapter_list = ChapterInfo.from_dict_list(item_list)
        return True

    async def _update_content_list(self) -> str:
        """通过章节列表对比，拉取新增章节以及版本更新章节"""
        api = await BotomatoAPI.get_instance()
        if len(self.chapter_list) > len(self.content_list):
            idx = len(self.content_list)
            for i in range(idx, len(self.chapter_list)):
                chapter = self.chapter_list[i]
                try:
                    data = await api.chapter(chapter.item_id)
                except Exception as e:
                    return f"拉取新章节《{self.info.book_name}》 第 {i} 章, {chapter.title} 时失败:\n{e}"
                self.content_list.append(ContentInfo.from_api_dict(chapter, data))
        for i in range(len(self.content_list)):
            chapter = self.chapter_list[i]
            content = self.content_list[i]
            if chapter.version != content.version:
                try:
                    data = await api.chapter(chapter.item_id)
                except Exception as e:
                    return f"更新章节《{self.info.book_name}》 第 {i} 章, {chapter.title} 时失败:\n{e}"
                self.content_list[i] = ContentInfo.from_api_dict(chapter, data)
        return f"《{self.info.book_name}》章节正文拉取成功"

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




