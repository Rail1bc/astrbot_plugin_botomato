from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Any, Dict
from datetime import datetime, timezone
import json


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        # Python's fromisoformat supports offsets like +08:00
        return datetime.fromisoformat(value)
    except Exception:
        # fallback: try to parse as epoch seconds
        try:
            ts = int(value)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            return None


def _parse_epoch_seconds(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        ts = int(value)
        # many timestamps in the dataset appear to be seconds since epoch
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        return None


@dataclass
class BookInfo:

    book_id: str    # 书籍 ID
    book_name: str  # 书名
    author: str     # 作者
    abstract: str = ""  # 简介
    tags: List[str] = field(default_factory=list)   # 标签列表
    word_number: Optional[int] = None   # 字数
    serial_count: Optional[int] = None  # 章节数
    score: Optional[float] = None   # 评分
    original_book_name: Optional[str] = None    # 原书名
    raw: Dict[str, Any] = field(default_factory=dict)   # 原始数据

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BookInfo":
        """从 API 返回的字典构造 BookInfo，尽量容错并解析常见格式。"""
        if data is None:
            raise ValueError("data is required")

        book_id = _to_str(data.get("book_id") or data.get("id") or "")
        book_name = _to_str(data.get("book_name") or data.get("title") or "")
        author = _to_str(data.get("author") or "")
        abstract = _to_str(data.get("abstract") or "")

        # tags 可能是逗号分隔字符串
        tags_raw = data.get("tags") or data.get("pure_category_tags") or ""
        if isinstance(tags_raw, str):
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        elif isinstance(tags_raw, list):
            tags = [str(t) for t in tags_raw]
        else:
            tags = []

        word_number = _to_int(data.get("word_number"))
        serial_count = _to_int(data.get("serial_count"))

        try:
            score_val = data.get("score")
            score = float(score_val) if score_val not in (None, "") else None
        except Exception:
            score = None

        original_book_name = _to_str(data.get("original_book_name") or "")

        return cls(
            book_id=book_id,
            book_name=book_name,
            author=author,
            abstract=abstract,
            tags=tags,
            word_number=word_number,
            serial_count=serial_count,
            score=score,
            original_book_name=original_book_name,
            raw=data,
        )



class Book:
    """Book 持有 BookInfo；未来可挂载章节、进度、缓存等行为。

    当前实现为一个轻量包装：提供访问、序列化等实用方法。
    """

    def __init__(self, info: BookInfo):
        self.info = info

    def __repr__(self) -> str:
        return f"<Book id={self.info.book_id!r} name={self.info.book_name!r} author={self.info.author!r}>"

    @classmethod
    def from_api_dict(cls, data: Dict[str, Any]) -> "Book":
        info = BookInfo.from_dict(data)
        return cls(info)
