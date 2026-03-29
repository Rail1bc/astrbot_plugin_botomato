from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from pathlib import Path
from .core.bookshelf.book import Book
from .core.bookshelf.bookshelf import BookShelf
from .core.command_handle.bookshelf_command import BookShelfCommandHandle
from .rain_api.rain_tomato_api import RainTomatoAPI

from astrbot.core.star.star_handler import star_handlers_registry



@register("astrbot_plugin_fanqie_novel", "Rail1bc", "让ai读小说，我是说让ai读，不是给你读", "0.1.0")
class FanqieNovel(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.config = config or {}
        self.data_path = (Path(get_astrbot_data_path()) / "plugin_data" / self.name)
        self.module_path = str((Path(get_astrbot_data_path()) / "plugins" / self.name))
        self.bookshelf: BookShelf = BookShelf(str(self.data_path / "bookshelf.db"))
        self.enable: bool = False
        self.reading_book: Book | None = None
        self.set_enable(False)

    # -------- 开启 ---------
    @filter.command("bookshelf", None, {"书架"})
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def bookshelf(self, event: AstrMessageEvent):
        """切换插件功能启用状态 /<书架|bookshelf> [on|off]"""
        args = event.message_str.split()
        if len(args) < 2:
            yield event.plain_result(self.set_enable())
        elif args[1] == "on":
            yield event.plain_result(self.set_enable(True))
        else:
            yield event.plain_result(self.set_enable(False))

    # -------- 搜书 ---------
    @filter.command("search_book",None,{"搜书"})
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def novel_search(self, event: AstrMessageEvent):
        """根据关键词搜索小说 /<搜书|search_book> <关键词> [页码|0]"""
        yield event.plain_result("正在搜索小说...")
        yield await BookShelfCommandHandle.novel_search(event)

    # -------- 书架操作 ---------
    @filter.command("add2shelf",None,{"加书架"})
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def add_book2shelf(self, event: AstrMessageEvent):
        """将书籍叫入到书架 /<加书架|add2shelf> <book_id>"""
        yield await BookShelfCommandHandle.add_book2shelf(event, self.bookshelf)

    @filter.command("rm_book", None, {"删书"})
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def remove_book(self, event: AstrMessageEvent):
        """删除书籍 /<删书|rm_book> <book_id>"""
        yield BookShelfCommandHandle.remove_book(event, self.bookshelf)

    @filter.command("update_bookshelf", None, {"更新书架"})
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def update_bookshelf(self, event: AstrMessageEvent):
        """更新书架内容 /<更新书架|update_bookshelf> [book_id]"""
        yield await BookShelfCommandHandle.update_bookshelf(event, self.bookshelf)

    @filter.command("show_bookshelf",None,{"看书架"})
    async def bookshelf_show(self, event: AstrMessageEvent):
        """展示书架内容 /<看书架|show_bookshelf> [关键词]"""
        yield await BookShelfCommandHandle.bookshelf_show(event, self.bookshelf)

    @filter.command("show_book_toc", None, {"看目录"})
    async def book_toc(self, event: AstrMessageEvent):
        """展示书籍目录 /<看目录|show_book_toc> <book_id> [页码|0]"""
        yield await BookShelfCommandHandle.show_book_toc(event, self.bookshelf)

    @filter.command("正文")
    async def book_chapter(self, event: AstrMessageEvent):
        book_id = event.message_str.split()[1]
        content = self.bookshelf.get_book(book_id).content_list[0].content
        logger.debug(content)
        yield event.plain_result(content)

    def set_enable(self, enable: bool = None):
        if bool is not None:
            self.enable = enable
        else:
            self.enable = not self.enable
        handlers = star_handlers_registry.get_handlers_by_module_name(self.module_path)
        logger.debug(self.module_path)
        logger.debug(handlers)
        for h in handlers:
            if h.handler_name != "bookshelf":
                h.enabled = self.enable
                logger.debug(f"设置 {h.handler_name} 可见性")
        return f"已{'启用' if self.enable else '禁用'} 🍅Botomato书架 功能"

    # -------- tool_call ---------


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
            try:
                books = await api.search("我的兄弟叫顺溜")
            except Exception as e:
                logger.warning(f"拉取测试失败，api不能正常工作:\n{e}")



    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        await RainTomatoAPI.destroy_instance()