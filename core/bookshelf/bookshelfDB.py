import os
import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

from .book import Book, ChapterInfo


class BookshelfDB:
    """书架数据库管理类，封装所有表操作"""

    def __init__(self, path: str):
        """
        初始化数据库连接，创建表结构并开启必要的 PRAGMA。
        """
        self.db_path = path
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # 使查询结果可像字典一样访问

        # 开启外键约束和 WAL 模式（提升并发与稳定性）
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")

        self._create_tables()

    def close(self):
        """关闭数据库连接"""
        self.conn.close()

    @contextmanager
    def transaction(self):
        """事务上下文管理器，自动提交或回滚"""
        try:
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def _create_tables(self):
        """创建四张表（如果不存在）"""
        cursor = self.conn.cursor()

        # 书籍表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                book_id TEXT PRIMARY KEY,
                book_name TEXT NOT NULL,
                alias_name TEXT,
                original_book_name TEXT,
                author TEXT,
                abstract TEXT,
                word_number INTEGER,
                serial_count INTEGER,
                read_cnt_text TEXT,
                score REAL
            )
        """)

        # 章节表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                book_id TEXT NOT NULL,
                idx INTEGER NOT NULL,
                item_id TEXT NOT NULL UNIQUE,
                version TEXT,
                title TEXT,
                volume_name TEXT,
                PRIMARY KEY (book_id, idx),
                FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE
            )
        """)
        # 为 item_id 创建索引（便于正文表查询）
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chapters_item_id ON chapters(item_id)")

        # 正文表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contents (
                item_id TEXT PRIMARY KEY,
                version TEXT,
                content TEXT NOT NULL
            )
        """)

        # 书签表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                book_id TEXT NOT NULL,
                bookmark_id INTEGER NOT NULL,   -- 0 表示默认书签
                bookmark_name TEXT,
                chapter_index INTEGER NOT NULL,
                PRIMARY KEY (book_id, bookmark_id),
                FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE
            )
        """)

        self.conn.commit()

    # ---------- 书籍操作 ----------

    def sync_book(self, book: Book) -> None:
        """
        同步书籍信息到数据库（插入或更新）。
        若书籍不存在则插入，若存在则更新所有字段。
        首次插入时自动创建默认书签（bookmark_id=0）。
        """
        info = book.info
        with self.transaction():
            # 插入或替换书籍信息
            self.conn.execute("""
                INSERT OR REPLACE INTO books (
                    book_id, book_name, alias_name, original_book_name,
                    author, abstract, word_number, serial_count, read_cnt_text, score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                info.book_id,
                info.book_name,
                info.alias_name,
                info.original_book_name,
                info.author,
                info.abstract,
                info.word_number,
                info.serial_count,
                info.read_cnt_text,
                info.score
            ))

            # 确保默认书签存在（仅当书籍首次添加时生效）
            self.conn.execute("""
                INSERT OR IGNORE INTO bookmarks (book_id, bookmark_id, bookmark_name, chapter_index)
                VALUES (?, 0, '上次阅读', 1)
            """, (info.book_id,))

    def get_book(self, book_id: str) -> Book:
        """获取单本书籍信息，返回 Book 对象"""
        cursor = self.conn.execute("SELECT * FROM books WHERE book_id = ?", (book_id,))
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Book not found: {book_id}")
        return Book.book_from_dict(dict(row))

    def search_books(self, keyword: str) -> List[Book]:
        """根据关键词搜索，任意条目包含关键词则算匹配"""
        query = """
                SELECT * FROM books
                WHERE book_name LIKE ?
                   OR alias_name LIKE ?
                   OR original_book_name LIKE ?
                   OR author LIKE ?
                   OR abstract LIKE ?
            """
        pattern = f"%{keyword}%"
        cursor = self.conn.execute(query, (pattern, pattern, pattern, pattern, pattern))
        books = []
        for row in cursor:
            books.append(Book.book_from_dict(dict(row)))
        return books


    def get_all_books(self) -> List[Book]:
        """获取所有书籍列表（按添加顺序），返回每本书的展示字符串"""
        cursor = self.conn.execute("SELECT * FROM books ORDER BY rowid")
        books = []
        for row in cursor:
            books.append(Book.book_from_dict(dict(row)))
        return books

    def delete_book(self, book_id: str) -> None:
        """删除书籍及其关联的章节、正文、书签（外键级联删除）"""
        with self.transaction():
            self.conn.execute("DELETE FROM books WHERE book_id = ?", (book_id,))

    # ---------- 章节操作 ----------

    def sync_chapters(self, book: Book) -> None:
        """
        将 book.chapter_list 同步到数据库。
        使用 INSERT OR REPLACE 实现插入或更新。
        """
        book_id = book.info.book_id
        with self.transaction():
            for idx, ch in enumerate(book.chapter_list, start=1):
                self.conn.execute("""
                    INSERT OR REPLACE INTO chapters (book_id, idx, item_id, version, title, volume_name)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (book_id, idx, ch.item_id, ch.version, ch.title, ch.volume_name))

    def get_chapters(self, book_id: str, offset: int = 0, limit: int = 100) -> list[ChapterInfo]:
        """
        分页获取某本书的章节列表，按 idx 排序。
        offset: 从 0 开始的偏移量（对应 idx-1）
        limit: 每页数量，默认 100
        """
        # offset 是行偏移，对应 idx 从 offset+1 开始
        cursor = self.conn.execute(
            "SELECT * FROM chapters WHERE book_id = ? ORDER BY idx LIMIT ? OFFSET ?",
            (book_id, limit, offset)
        )
        return [ChapterInfo.from_api_dict(dict(row)) for row in cursor]

    def get_all_chapters(self, book_id: str) -> list[ChapterInfo]:
        """获取某本书的全部章节（按 idx 排序）"""
        cursor = self.conn.execute(
            "SELECT * FROM chapters WHERE book_id = ? ORDER BY idx",
            (book_id,)
        )
        return [ChapterInfo.from_api_dict(dict(row)) for row in cursor]

    def get_chapter(self, book_id: str, idx: int) -> ChapterInfo:
        """根据书籍 ID 和章节索引获取单个章节信息"""
        cursor = self.conn.execute(
            "SELECT * FROM chapters WHERE book_id = ? AND idx = ?", (book_id, idx)
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Chapter not found: book_id={book_id}, idx={idx}")
        return ChapterInfo.from_api_dict(dict(row))

    # ---------- 正文操作 ----------
    def get_content(self, item_id: str) -> Optional[str]:
        """获取章节正文"""
        cursor = self.conn.execute("SELECT * FROM contents WHERE item_id=?", (item_id,))
        row = cursor.fetchone()
        return row['content'] if row else None

    def set_content(self, item_id: str, content: str) -> None:
        """存储或更新章节正文"""
        with self.transaction():
            self.conn.execute("""
                INSERT OR REPLACE INTO contents (item_id, content) VALUES (?, ?)
            """, (item_id, content))

    # ---------- 书签操作 ----------
    def get_default_bookmark(self, book_id: str) -> int:
        """获取默认书签（当前阅读进度）对应的章节下标，若不存在则返回 1"""
        cursor = self.conn.execute(
            "SELECT chapter_index FROM bookmarks WHERE book_id=? AND bookmark_id=0", (book_id,)
        )
        row = cursor.fetchone()
        return row['chapter_index'] if row else 1

    def update_default_bookmark(self, book_id: str, chapter_index: int) -> None:
        """更新默认书签（当前阅读进度）"""
        with self.transaction():
            self.conn.execute("""
                INSERT OR REPLACE INTO bookmarks (book_id, bookmark_id, bookmark_name, chapter_index)
                VALUES (?, 0, '上次阅读', ?)
            """, (book_id, chapter_index))

    def add_custom_bookmark(self, book_id: str, bookmark_name: str, chapter_index: int) -> int:
        """
        添加自定义书签，自动分配一个非零的 bookmark_id（最小可用正整数）
        :return: 新书签的 bookmark_id
        """
        with self.transaction():
            # 找出当前 book_id 下最大的 bookmark_id（不包括 0）
            cursor = self.conn.execute(
                "SELECT MAX(bookmark_id) FROM bookmarks WHERE book_id=? AND bookmark_id!=0",
                (book_id,)
            )
            max_id = cursor.fetchone()[0] or 0
            new_id = max_id + 1
            self.conn.execute("""
                INSERT INTO bookmarks (book_id, bookmark_id, bookmark_name, chapter_index)
                VALUES (?, ?, ?, ?)
            """, (book_id, new_id, bookmark_name, chapter_index))
            return new_id

    def delete_custom_bookmark(self, book_id: str, bookmark_id: int) -> None:
        """删除自定义书签（bookmark_id 不能为 0）"""
        if bookmark_id == 0:
            raise ValueError("不能删除默认书签")
        with self.transaction():
            self.conn.execute(
                "DELETE FROM bookmarks WHERE book_id=? AND bookmark_id=?",
                (book_id, bookmark_id)
            )

    def get_all_bookmarks(self, book_id: str) -> List[Dict[str, Any]]:
        """获取某本书的所有书签（包含默认书签，默认书签排最前）"""
        cursor = self.conn.execute("""
            SELECT * FROM bookmarks WHERE book_id=?
            ORDER BY bookmark_id = 0 DESC, bookmark_id
        """, (book_id,))
        return [dict(row) for row in cursor.fetchall()]

    # ---------- 工作流程辅助方法（可选） ----------