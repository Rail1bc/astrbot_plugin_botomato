from .book import Book, ChapterInfo
from .bookshelfDB import BookshelfDB



class BookShelf:
    def __init__(self, path: str):
        self.DB = BookshelfDB(path)

    async def add_book(self, book: Book):
        """
        将某书添加进书架
        同时添加章节列表
        """
        self.DB.sync_book(book)
        if await book.update_chapter_list():
            self.DB.sync_chapters(book)
            return f"已将《{book.info.book_name}》加入书架。"
        else:
            return f"已将《{book.info.book_name}》加入,但章节列表拉取失败。"


    def show_book(self, keyword: str | None) -> str:
        """
        展示书架存书
        如果存在keyword，则只展示书籍信息包含keyword的书
        """
        if not keyword:
            return "书架藏书：\n\n" + "\n\n".join(
                [book.book_info_to_str() for book in self.DB.get_all_books()]
            )
        else:
            return "书架藏书匹配结果：\n\n" + "\n\n".join(
                [book.book_info_to_str() for book in self.DB.search_books(keyword)]
            )

    async def update_book(self, book_id: str | None) -> str:
        """
        更新书架存书
        如果不传入参数，则更新全部的书
        """
        if book_id is None:
            books = self.DB.get_all_books()
            result = []
            for book in books:
                result.append(await book.update())
                self.DB.sync_book(book)
                self.DB.sync_chapters(book)
                self.DB.sync_content(book)
            result = "\n--------\n".join(result)
            return f"已更新书架全部书籍\n更新情况：\n{result}"
        try:
            book = self.DB.get_book(book_id)
            result = await book.update()
            self.DB.sync_book(book)
            self.DB.sync_chapters(book)
            self.DB.sync_content(book)
        except Exception as e:
            return str(e)
        return f"已更新书籍《{book.info.book_name}》\n更新情况:\n{result}"


    def delete_book(self, book_id: str) -> str:
        """
        从书架删除书籍
        """
        try:
            self.DB.delete_book(book_id)
            return f"已删除书籍ID为 {book_id} 的书籍。"
        except Exception as e:
            return str(e)

    def get_book(self, book_id: str) -> Book:
        return self.DB.get_book(book_id)

    def get_chapters(self, book_id: str, page: int = 1, limit: int = 100) -> list[ChapterInfo]:
        return self.DB.get_chapters(book_id, page, limit)