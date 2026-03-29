from ..bookshelf.book import Book
from ..bookshelf.bookshelf import BookShelf
from ...rain_api.rain_tomato_api import RainTomatoAPI


class BookShelfHandle:

    @staticmethod
    async def novel_search(keywords: str, page: int = 0) -> str:
        # 调用API搜索书籍
        api = await RainTomatoAPI.get_instance()
        try:
            books_data = await api.search(keywords, page)
        except Exception as e:
            return f"搜索请求失败:\n{e}"
        book_list = Book.list_from_dict(books_data)

        # 处理结果
        result = (
                "搜索结果：\n----------\n" +
                "\n----------\n".join(
                    [f"{i + 1}. {book.book_info_to_str()}" for i, book in enumerate(book_list)]
                )
        )
        return result

    @staticmethod
    async def add_book2shelf(book_id: str, bookshelf: BookShelf) -> str:
        # 构造Book并存入书架
        book_or_msg = await BookShelfHandle._search_book_by_id(book_id)
        if isinstance(book_or_msg, str):
            return book_or_msg
        book: Book = book_or_msg
        return await bookshelf.add_book(book)

    @staticmethod
    async def show_book_toc(book_id: str, bookshelf: BookShelf, page: int = 1, limit: int = 100) -> str:
        chapters = bookshelf.get_chapters(book_id, page, limit)
        return "章节列表:\n" + "\n".join([f"{chapter.title}" for i, chapter in enumerate(chapters)])

    @staticmethod
    async def _search_book_by_id(book_id: str) -> Book | str:
        try:
            return await Book.from_bookid(book_id)
        except TypeError as e:
            return str(e)