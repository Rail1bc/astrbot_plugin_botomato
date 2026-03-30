from os import name

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from pathlib import Path

from astrbot.core.star.star_handler import star_handlers_registry
from .core.handle.bookshelf_handle import BookShelfHandle
from .core.bookshelf.book import Book
from .core.bookshelf.bookshelf import BookShelf
from .core.handle.bookshelf_command import BookShelfCommandHandle
from .botomato_api.botomato_api import BotomatoAPI




@register("astrbot_plugin_fanqie_novel", "Rail1bc", "让ai读小说，我是说让ai读，不是给你读", "0.1.0")
class FanqieNovel(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.config = config or {}
        self.data_path = (Path(get_astrbot_data_path()) / "plugin_data" / self.name)
        self.module_path = "data.plugins.astrbot_plugin_fanqie_novel.main"
        self.bookshelf: BookShelf = BookShelf(str(self.data_path / "bookshelf.db"))
        self.enable: bool = False
        self.reading_book: Book | None = None
        self.command_set = {"Botomato", "search_book", "add2shelf", "rm_book", "update_bookshelf", "show_bookshelf", "show_book_toc"}
        self.tool_set = {"Botomato_tool_status", "search_novel", "add_novel2shelf", "look_novel_toc", "Botomato_take_book"}
        self.gate = {"Botomato", "Botomato_tool_status"}
        self.switch = {"Botomato", "Botomato_tool_status", "Botomato_take_book"}
        self.reading_tool = {"look_toc", "read_book", "move_bookmark", "read_chapter"}
        self.set_enable(False)

    # -------- 开启 ---------
    @filter.command("Botomato", None, {"书架"})
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
        """展示书籍目录 /<看目录|show_book_toc> <book_id> [起始|1] [查询条目数|100]"""
        yield await BookShelfCommandHandle.show_book_toc(event, self.bookshelf)

    # -------- tool_call ---------
    @filter.llm_tool(name="Botomato_tool_status")
    async def botomato_bookshelf(self, event: AstrMessageEvent, status: bool):
        """
        Botomato书架工具开关，当需要阅读、搜索小说等，涉及小说信息的功能时使用

        Args:
            status (bool): 必填 工具开关状态，true表示开启工具，false表示关闭工具
        """
        self.set_enable(status)


    @filter.llm_tool(name="search_novel")
    async def call_search_novel(self, event: AstrMessageEvent, keywords: str, page: int = 0) :
        """
        搜索小说基础信息(包括book_id、书名、简介等)，当需要根据关键词搜索小说时，调用该工具。

        Args:
            keywords (str): 必填 搜索关键词，支持小说名、简介，不支持作者名
            page (int): 选填 搜索分页，默认0
        """
        return await BookShelfHandle.novel_search(keywords, page)

    @filter.llm_tool(name="add_novel2shelf")
    async def call_add_novel2shelf(self, event: AstrMessageEvent, book_id: str):
        """
        将小说加入书架，当需要将小说加入书架时，调用该工具。

        Args:
            book_id (str): 必填 书籍ID
        """
        return await BookShelfHandle.add_book2shelf(book_id, self.bookshelf)

    @filter.llm_tool(name="add_novel2shelf")
    async def call_show_bookshelf(self, event: AstrMessageEvent, keywords: str = None):
        """
        查看书架藏书(包括book_id、书名、简介等)，当需要查看书架内容时，调用该工具。

        Args:
            keywords (str): 选填 关键词，支持包括书籍id、书名、作者名的多个字段匹配
        """
        return self.bookshelf.show_book(keywords)

    @filter.llm_tool(name="look_novel_toc")
    async def call_look_novel_toc(self, event: AstrMessageEvent, book_id: str, page: int = 1, limit: int = 100):
        """
        查看小说目录，当需要查看书架中小说的目录时，调用该工具。

        Args:
            book_id (str): 必填 书籍ID
            page (int): 选填 起始章节，默认1
            limit (int): 选填 查询量，默认100
        """
        return await BookShelfHandle.show_book_toc(book_id, self.bookshelf, page, limit)

    @filter.llm_tool(name="Botomato_take_book")
    async def call_take_book(self, event: AstrMessageEvent, book_id: str = ""):
        """
        取书或收书，当需要阅读书架中的书籍时取书，当不需要阅读时收起

        Args:
            book_id (str): 选填 要取的书籍的id，不填时表示收起
        """
        return self.set_reading_book(book_id)



    def set_reading_book(self, book_id: str = ""):
        if not book_id:
            self.reading_book = None
            self.set_reading_tool_enable(False)
            return "已收起书籍，书架操作能力已恢复，读书能力已关闭。"

        self.reading_book = self.bookshelf.get_book(book_id)
        self.set_reading_tool_enable(True)
        return f"已取出书籍《{self.reading_book.info.book_name}》\n书架操作能力已关闭，读书能力已开启。"

    def set_tool_status(self, status: str):
        handlers = star_handlers_registry.get_handlers_by_module_name(self.module_path)
        if status == "off":
            for h in handlers:
                if h.handler_name in self.tool_set:
                    h.enabled = False
            return "Botomato书架能力已关闭。"
        elif status == "on":
            for h in handlers:
                if h.handler_name in (self.tool_set - self.reading_tool):
                    h.enabled = True
                elif h.handler_name in self.reading_tool:
                    h.enabled = False
        elif status == "reading":
            for h in handlers:
                if h.handler_name in (self.tool_set - self.reading_tool - self.switch):
                    h.enabled = False
                elif h.handler_name in self.reading_tool:
                    h.enabled = True

    def set_command_status(self, status: str):
        if status == "off":
            for h in handlers:

    def set_enable(self, enable: bool = None):
        if enable is not None:
            self.enable = enable
        else:
            self.enable = not self.enable
        handlers = star_handlers_registry.get_handlers_by_module_name(self.module_path)
        for h in handlers:
            if h.handler_name not in self.gate:
                h.enabled = self.enable
                logger.debug(f"设置 {h.handler_name} 可见性")
        return f"已{'启用' if self.enable else '禁用'} 🍅Botomato书架 能力"

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        # 初始化 api
        base_url = self.config.get("novel_resource_base")
        api = await BotomatoAPI.get_instance(base_url=base_url)
        logger.debug("api 初始化完成")
        try:
            await api.search("我的兄弟叫顺溜")
        except Exception as e:
            logger.warning(f"拉取测试失败，api不能正常工作:\n{e}")



    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        await BotomatoAPI.destroy_instance()