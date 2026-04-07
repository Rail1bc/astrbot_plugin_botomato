from typing import Optional, Any, Dict, List

from .bookRepository import BookRepository
from .book_info import BookInfo, ChapterInfo, ContentInfo
from ...botomato_api.botomato_api import BotomatoAPI


class Book:
    """
    Book 书籍类
    """

    def __init__(
            self, info: BookInfo,
            toc: List[ChapterInfo] = [],
            chapters: List[ContentInfo] = [],
            bookmark: int = 1
    ) -> None:
        self.info = info
        self.chapter_list: Optional[List[ChapterInfo]] = toc
        self.content_list: Optional[List[ContentInfo]] = chapters
        self.bookmark = bookmark

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
        return [Book.from_dict(data) for data in data_list]

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

    # ---------- 查询方法 ---------------

    def info_to_str(self) -> str:
        """
        将书籍信息反序列化为 适合在聊天中展示的字符串
        """
        parts = []
        parts.append(f"《{self.info.book_name}》")
        parts.append(f"作者：{self.info.author}")
        parts.append(f"评分：{self.info.score}")
        parts.append(f"在读：{self.info.read_cnt_text}")
        parts.append(f"书籍id:{self.info.book_id}")
        parts.append(self.info.abstract.strip())
        return "\n* ".join(parts) if parts else repr(self)

    def toc_to_str(self, offset: int = 1, limit: int = -1) -> str:
        """
        将章节列表反序列化为 适合在聊天中展示的字符串
        """
        chapters = self.chapter_list[offset - 1:]
        if limit != -1:
            chapters = chapters[:limit]
        return "章节列表:\n" + "\n".join([f"{offset + i}:{chapter.title}" for i, chapter in enumerate(chapters)])

    async def read(self) -> str:
        """
        阅读正文
        """
        # 如果书签位置超过章节列表长度，检查是对应章节是否存在
        if len(self.content_list) < self.bookmark :
            if len(self.chapter_list) < self.bookmark :
                return f"已经阅读到最新章！作者还没更新！"
            else :
                api = await BotomatoAPI.get_instance()
                chapter = self.chapter_list[self.bookmark - 1]
                try:
                    data = await api.chapter(chapter.item_id)
                except Exception as e:
                    return f"拉取新章节《{self.info.book_name}》 {self.bookmark}, {chapter.title} 时失败:\n{e}"
                self.content_list.append(ContentInfo.from_api_dict(chapter, data))
                self.save_chapters()

        content = self.content_list[self.bookmark - 1]
        self.bookmark += 1
        self.save_bookmark()
        return content.to_str()

    def set_bookmark(self, bookmark: int) :
        self.bookmark = bookmark
        self.save_bookmark()
        return f"已将《{self.info.book_name}》的书签移动至{bookmark}"


    def read_chapter(self, index: int):
        return self.content_list[index - 1].to_str()

    # --------- 持久化存储方法 --------------
    def save(self):
        """将书籍信息保存"""
        self.save_book_info()
        self.save_toc()
        self.save_chapters()
        self.save_bookmark()

    def save_book_info(self):
        """保存书籍基础信息"""
        BookRepository().sync_book_info(self.info)

    def save_toc(self):
        """保存书籍章节列表"""
        BookRepository().sync_chapters(self.info.book_id, self.chapter_list)

    def save_chapters(self):
        """报错书籍正文内容"""
        BookRepository().sync_content(self.info.book_id, self.content_list)

    def save_bookmark(self):
        """保存书籍书签位置"""
        BookRepository().update_default_bookmark(self.info.book_id, self.bookmark)