from .book import Book
from .bookshelfDB import BookshelfDB



class BookShelf:
    def __init__(self):
        self.DB = BookshelfDB()

    async def add_book(self, book: Book):
        """
        将某书添加进书架
        同时添加章节列表
        """
        self.DB.sync_book(book)
        await book.update_chapter_list()
        self.DB.sync_chapters(book)

    def show_book(self, keyword: str | None) -> str:
        """
        展示书架存书
        如果存在keyword，则只展示书籍信息包含keyword的书
        """
        if keyword is None:
            return "书架存书：\n\n" + "\n\n".join(
                [book.book_info_to_str() for book in self.DB.get_all_books()]
            )
        else:
            return "书架存书匹配结果：\n\n" + "\n\n".join(
                [book.book_info_to_str() for book in self.DB.search_books(keyword)]
            )

    async def update_book(self, book_id: str | None) -> str:
        """
        更新书架存书
        如果不传入参数，则更新全部的书
        """
        if book_id is None:
            books = self.DB.get_all_books()
            for book in books:
                await book.update()
                self.DB.sync_book(book)
                self.DB.sync_chapters(book)
            return "已更新书架全部书籍信息"
        try:
            book = self.DB.get_book(book_id)
            await book.update()
            self.DB.sync_book(book)
            self.DB.sync_chapters(book)
            return f"已更新书籍《{book.info.book_name}》信息"
        except Exception as e:
            return str(e)

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