from astrbot.api.event import AstrMessageEvent

from ..bookshelf.book import Book
from ...core.bookshelf.bookshelf import BookShelf
from ...rain_api.rain_tomato_api import RainTomatoAPI

class NovelCommandHandle:

    # ---------- 搜书 -----------
    @staticmethod
    async def novel_search(event: AstrMessageEvent):
        """根据关键词搜索小说 /搜书 <关键词> [页码|0]"""
        args = event.message_str.split()
        if (args is None) or (len(args) < 2):
            return event.plain_result("请提供搜索关键词，格式：\n/搜书 <关键词> [页码|0]")
        keywords = args[1]
        page = int(args[2]) if len(args) > 2 and args[2].isdigit() else 0
        result = await NovelCommandHandle._search_book_by_keywords(keywords, page)
        return event.plain_result(result)

    @staticmethod
    async def _search_book_by_keywords(keywords: str, page: int = 0) -> str:
        """根据关键字搜索小说"""
        api = await RainTomatoAPI.get_instance()

        if (api is None) or (api.enable is False):
            return "api失效，无法更新、获取新的书籍信息。"

        books_data = await api.search(keywords, page)
        book_list = Book.book_list_from_dict(books_data)

        result = ("搜索结果：\n----------\n" +
               "\n----------\n".join([f"{i+1}. {book.book_info_to_str()}" for i, book in enumerate(book_list)]))
        return result


    # ---------- 加书架 -----------
    @staticmethod
    async def add_book2shelf(event: AstrMessageEvent, bookshelf: BookShelf):
        """将书籍加入到书架 /加书架 <book_id>"""
        args = event.message_str.split()
        if (args is None) or (len(args) < 2):
            return event.plain_result("请提供书籍ID，格式：\n/加书架 <book_id>")
        book_id = args[1]
        result = await NovelCommandHandle._add_book_to_shelf(book_id, bookshelf)
        return event.plain_result(result)

    @staticmethod
    async def _add_book_to_shelf(book_id: str, bookshelf: BookShelf) -> str:
        """将书籍加入到书架"""
        book_or_msg = await NovelCommandHandle._search_book_by_id(book_id)
        if isinstance(book_or_msg, str):
            return book_or_msg
        book: Book = book_or_msg
        await bookshelf.add_book(book)
        return f"已将《{book.info.book_name}》加入书架。"

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







    @staticmethod
    async def _search_book_by_id(book_id: str) -> Book | str:
        try:
            return await Book.book_from_bookid(book_id)
        except Exception as e:
            return str(e)