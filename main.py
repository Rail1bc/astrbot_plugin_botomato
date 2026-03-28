from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.star.filter.permission import PermissionType
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from pathlib import Path
from .core.bookshelf.book import Book
from .core.bookshelf.bookshelf import BookShelf
from .core.command_handle.novel_command import NovelCommandHandle
from .rain_api.rain_tomato_api import RainTomatoAPI


@register("astrbot_plugin_fanqie_novel", "Rail1bc", "让ai读小说，我是说让ai读，不是给你读", "0.1.0")
class FanqieNovel(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.config = config or {}
        self.data_path = (Path(get_astrbot_data_path()) / "plugin_data" / self.name)
        self.bookshelf: BookShelf = BookShelf(str(self.data_path / "bookshelf.db"))
        self.reading_book: Book | None = None

    # -------- 搜书 ---------
    @filter.command("search_book",None,{"搜书"})
    @filter.permission_type(PermissionType.ADMIN)
    async def novel_search(self, event: AstrMessageEvent):
        """根据关键词搜索小说 /<搜书|search_book> <关键词> [页码|0]"""
        yield NovelCommandHandle.novel_search(event)

    # -------- 书架操作 ---------
    @filter.command("add2shelf",None,{"加书架"})
    @filter.permission_type(PermissionType.ADMIN)
    async def add_book2shelf(self, event: AstrMessageEvent):
        """将书籍叫入到书架 /<加书架|add2shelf> <book_id>"""
        yield NovelCommandHandle.add_book2shelf(event, self.bookshelf)

    @filter.command("rm_book", None, {"删书"})
    @filter.permission_type(PermissionType.ADMIN)
    async def remove_book(self, event: AstrMessageEvent):
        """删除书籍 /<删书|rm_book> <book_id>"""
        NovelCommandHandle.remove_book(event, self.bookshelf)

    @filter.command("update_bookshelf", None, {"更新书架"})
    @filter.permission_type(PermissionType.ADMIN)
    async def update_bookshelf(self, event: AstrMessageEvent):
        """更新书架内容 /<更新书架|update_bookshelf> [book_id]"""
        yield NovelCommandHandle.update_bookshelf(event, self.bookshelf)

    @filter.command("show_bookshelf",None,{"看书架"})
    async def bookshelf_show(self, event: AstrMessageEvent):
        """展示书架内容 /<看书架|show_bookshelf> [关键词]"""
        yield NovelCommandHandle.bookshelf_show(event, self.bookshelf)


    # -------- 读书操作 ---------
    @filter.command("read_book",None,{"读书"})
    @filter.permission_type(PermissionType.ADMIN)
    async def read_book(self, event: AstrMessageEvent):
        """进入读书状态 /<读书|read_book> <book_id>"""

    @filter.command("bookshelf",None,{"书架", "bs"})
    @filter.permission_type(PermissionType.ADMIN)
    async def bookshelf(self, event: AstrMessageEvent):
        """操作当前所读的书 /<书架|bs> [参数]"""



    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        # 初始化 api
        apikey = self.config.get("rain_api_key")
        base_url = self.config.get("novel_resource_base")
        if not apikey:
            logger.warning("没有 api key ,无法更新、获取新的书籍信息。")
        else:
            api = await RainTomatoAPI.get_instance(apikey,base_url=base_url)
            logger.debug("api 初始化完成")
            books = await api.search("我的兄弟叫顺溜")



    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        await RainTomatoAPI.destroy_instance()