from astrbot.api.event import AstrMessageEvent

from .bookshelf_handle import BookShelfHandle
from ..bookshelf.book import Book
from ...core.bookshelf.bookshelf import BookShelf

class BookShelfCommandHandle:

    # ---------- 搜书 -----------
    @staticmethod
    async def novel_search(event: AstrMessageEvent):
        """根据关键词搜索小说 /搜书 <关键词> [页码|0]"""
        # 解析参数
        args = event.message_str.split()
        if (args is None) or (len(args) < 2):
            return event.plain_result("请提供搜索关键词，格式：\n/搜书 <关键词> [页码|0]")
        keywords = args[1]
        page = int(args[2]) if len(args) > 2 and args[2].isdigit() else 0
        # 搜索结果
        result = BookShelfHandle.novel_search(keywords, page)
        return event.plain_result(result)

    # ---------- 加书架 -----------
    @staticmethod
    async def add_book2shelf(event: AstrMessageEvent, bookshelf: BookShelf):
        """将书籍加入到书架 /加书架 <book_id>"""
        # 解析参数
        args = event.message_str.split()
        if (args is None) or (len(args) < 2):
            return event.plain_result("请提供书籍ID，格式：\n/加书架 <book_id>")
        book_id = args[1]
        # 操作
        result = await BookShelfHandle.add_book2shelf(book_id, bookshelf)
        return event.plain_result(result)

    # ----------- 删除书籍 ------------
    @staticmethod
    def remove_book(event: AstrMessageEvent, bookshelf: BookShelf):
        """删除书籍 /删书 <book_id>"""
        args = event.message_str.split()
        if (args is None) or (len(args) < 2):
            return event.plain_result("请提供书籍ID，格式：\n/删书 <book_id>")
        book_id = args[1]
        return event.plain_result(bookshelf.DB.delete_book(book_id))

    # ---------- 更新书架 ------------
    @staticmethod
    async def update_bookshelf(event: AstrMessageEvent, bookshelf: BookShelf):
        """更新书架内容 /更新书架 [book_id]"""
        args = event.message_str.split()
        book_id = args[1] if len(args) > 1 else None
        result = await bookshelf.update_book(book_id)
        return event.plain_result(result)

    # ---------- 展示书架 -----------
    @staticmethod
    async def bookshelf_show(event: AstrMessageEvent, bookshelf: BookShelf):
        """展示书架内容 /看书架 [关键词]"""
        args = event.message_str.split()
        keyword = args[1] if len(args) > 1 else None
        result = bookshelf.show_book(keyword)
        return event.plain_result(result)

    # ---------- 看目录 ------------
    @staticmethod
    async def show_book_toc(event: AstrMessageEvent, bookshelf: BookShelf):
        """展示书籍目录 /看目录 <book_id> [起始|1]"""
        args = event.message_str.split()
        if (args is None) or (len(args) < 2):
            return event.plain_result("请提供书籍ID，格式：\n/看目录 <book_id> [起始|1]")
        book_id = args[1]
        page = int(args[2]) if len(args) > 2 and args[2].isdigit() else 1
        limit = int(args[3] if len(args) > 3 and args[2].isdigit() else 100)
        result = BookShelfHandle.show_book_toc(book_id,bookshelf,page,limit)
        return event.plain_result(result)

    # --------- 辅助方法
    @staticmethod
    async def _search_book_by_id(book_id: str) -> Book | str:
        try:
            return await Book.from_bookid(book_id)
        except TypeError as e:
            return str(e)