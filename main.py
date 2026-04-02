from multiprocessing.util import debug
from os import name

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from pathlib import Path

from astrbot.core.star.star_handler import star_handlers_registry

from .core.bookshelf.bookRepository import BookRepository
from .core.handle.bookshelf_handle import BookShelfHandle
from .core.bookshelf.book import Book
from .core.bookshelf.bookshelf import BookShelf
from .core.handle.bookshelf_command import BookShelfCommandHandle
from .botomato_api.botomato_api import BotomatoAPI




@register("astrbot_plugin_botomato", "Rail1bc", "给bot读书用的虚拟书架!", "0.1.0")
class BotomatoPlugin(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.config = config or {}
        self.data_path = (Path(get_astrbot_data_path()) / "plugin_data" / self.name)
        BookRepository.set_db_path(str(self.data_path / "bookshelf.db"))
        self.module_path = "data.plugins.astrbot_plugin_botomato.main"
        self.enable: bool = False
        self.reading_book: Book | None = None
        self.gate = {"Botomato"}    # 总开关
        self.switch = {"Botomato_tool_status"}    # tool开关
        self.bookshelf_tool = {"Botomato_tool_status", "search_book", "add_book2shelf", "look_book_toc", "remove_book4shelf", "Botomato_take_book"}
        self.take_tool = {"Botomato_take_book"}
        self.reading_tool = {"look_book", "look_toc", "read_book", "move_bookmark", "read_chapter"}
        self.set_enable(False)

    # -------- 开启 ---------
    @filter.command("Botomato", None, {"书架"})
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def bookshelf(self, event: AstrMessageEvent):
        """总控制，切换插件功能启用状态 /<书架|bookshelf> [on|off]"""
        args = event.message_str.split()
        if len(args) < 2:
            yield event.plain_result(self.set_enable())
        elif args[1] == "on":
            yield event.plain_result(self.set_enable(True))
        else:
            yield event.plain_result(self.set_enable(False))

    # -------- 搜书 ---------
    @filter.command("search_book", None, {"搜书"})
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def novel_search(self, event: AstrMessageEvent):
        """根据关键词搜索小说 /<搜书|search_book> <关键词> [页码|0]"""
        yield event.plain_result("正在搜索小说...")
        yield await BookShelfCommandHandle.novel_search(event)

    # -------- 书架操作 ---------
    @filter.command("add2shelf", None, {"加书架"})
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def add_book2shelf(self, event: AstrMessageEvent):
        """将书籍叫入到书架 /<加书架|add2shelf> <book_id>"""
        yield await BookShelfCommandHandle.add_book2shelf(event)

    @filter.command("rm_book", None, {"删书"})
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def remove_book(self, event: AstrMessageEvent):
        """删除书籍 /<删书|rm_book> <book_id>"""
        yield BookShelfCommandHandle.remove_book(event)

    @filter.command("update_bookshelf", None, {"更新书架"})
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def update_bookshelf(self, event: AstrMessageEvent):
        """更新书架内容 /<更新书架|update_bookshelf> [book_id]"""
        yield await BookShelfCommandHandle.update_bookshelf(event)

    @filter.command("show_bookshelf",None,{"看书架"})
    async def bookshelf_show(self, event: AstrMessageEvent):
        """展示书架内容 /<看书架|show_bookshelf> [关键词]"""
        yield await BookShelfCommandHandle.bookshelf_show(event)

    @filter.command("show_book_toc", None, {"看目录"})
    async def book_toc(self, event: AstrMessageEvent):
        """展示书籍目录 /<看目录|show_book_toc> <book_id> [起始|1] [查询条目数|100]"""
        yield await BookShelfCommandHandle.show_book_toc(event)

    # -------- tool_call ---------
    @filter.llm_tool(name="Botomato_tool_status")
    async def botomato_bookshelf(self, event: AstrMessageEvent, status: bool):
        """
        Botomato书架总开关，Botomato书架是属于bot的小说书架。

        Args:
            status (bool): 必填 开关状态，true表示开启工具，false表示关闭工具
        """
        return self.set_tool_status("on" if status else "off")


    @filter.llm_tool(name="search_book")
    async def call_search_novel(self, event: AstrMessageEvent, keywords: str, page: int = 0) :
        """
        搜索小说基础信息(包括book_id、书名、简介等，不包括目录、正文)。

        Args:
            keywords (str): 必填 搜索关键词，支持小说名、简介，不支持作者名
            page (int): 选填 搜索分页，默认0
        """
        return await BookShelfHandle.novel_search(keywords, page)

    @filter.llm_tool(name="add_book2shelf")
    async def call_add_novel2shelf(self, event: AstrMessageEvent, book_id: str):
        """
        将小说加入书架。

        Args:
            book_id (str): 必填 书籍ID
        """
        return await BookShelfHandle.add_book2shelf(book_id)

    @filter.llm_tool(name="show_book4shelf")
    async def call_show_bookshelf(self, event: AstrMessageEvent, keywords: str = None):
        """
        查看书架藏书(包括book_id、书名、简介等)。

        Args:
            keywords (str): 选填 关键词，支持包括书籍id、书名、作者名的多个字段匹配
        """
        return BookShelf.show_book(keywords)

    @filter.llm_tool(name="look_book_toc")
    async def call_look_novel_toc(self, event: AstrMessageEvent, book_id: str, offset: int = 1, limit: int = 100):
        """
        查看小说目录，只能查看书架内的小说。

        Args:
            book_id (str): 必填 书籍ID
            offset (int): 选填 起始章节，默认1
            limit (int): 选填 查询量，默认100
        """
        return BookShelf.get_book(book_id).toc_to_str(offset, limit)

    @filter.llm_tool(name="remove_book4shelf")
    async def call_remove_book4shelf(self, event: AstrMessageEvent, book_id: str):
        """
        从书架删除指定藏书

        Args:
            book_id (str): 必填 书籍ID
        """
        return BookShelf.delete_book(book_id)

    # -------- reading tool --------

    @filter.llm_tool(name="Botomato_take_book")
    async def call_take_book(self, event: AstrMessageEvent, book_id: str = ""):
        """
        从书架取一本书，以进一步阅读或其他操作。

        Args:
            book_id (str): 选填 要取的书籍的id，不填时表示收起
        """
        return self.set_reading_book(book_id)

    @filter.llm_tool(name="look_book")
    async def look_book(self, event: AstrMessageEvent):
        """
        查看当前书籍的基础信息
        """
        return self.reading_book.info_to_str()

    @filter.llm_tool(name="look_toc")
    async def look_book(self, event: AstrMessageEvent, offset: int = 1, limit: int = 100):
        """
        查看当前书籍的目录
        
        Args:
            offset (int): 选填 起始章节，默认1
            limit (int): 选填 查询量，默认100
        """
        return self.reading_book.toc_to_str(offset, limit)

    @filter.llm_tool(name="read_book")
    async def read_book(self, event: AstrMessageEvent):
        """
        自动接续进度阅读当前书籍，会自动移动书签，无需任何参数
        """
        return self.reading_book.read()

    @filter.llm_tool(name="move_bookmark")
    async def move_bookmark(self, event: AstrMessageEvent, index: int = 1):
        """
        移动书签到指定章节

        Args:
            index (int): 选填 章节序号，默认1
        """
        return self.reading_book.set_bookmark(index)

    @filter.llm_tool(name="read_chapter")
    async def read_chapter(self, event: AstrMessageEvent, index: int = 1):
        """
        阅读指定章节

        Args:
            index (int): 选填 章节序号，默认1
        """
        return self.reading_book.read_chapter(index)

    def set_reading_book(self, book_id: str = ""):
        if not book_id:
            self.reading_book = None
            return self.set_tool_status("on")

        self.reading_book = BookShelf.get_book(book_id)
        result = self.set_tool_status("reading")
        return f"已取出书籍《{self.reading_book.info.book_name}》\n{result}"

    def set_tool_status(self, status: str):
        handlers = star_handlers_registry.get_handlers_by_module_name(self.module_path)
        if status == "off":
            for h in handlers:
                if h.handler_name in (self.bookshelf_tool | self.take_tool | self.reading_tool):
                    h.enabled = False
            return "已退出Botomato书架"
        elif status == "on":
            for h in handlers:
                if h.handler_name in (self.bookshelf_tool | self.take_tool | self.switch):
                    h.enabled = True
                elif h.handler_name in self.reading_tool:
                    h.enabled = False
            return "现在可以管理Botomato书架！"
        elif status == "reading":
            for h in handlers:
                if h.handler_name in self.bookshelf_tool:
                    h.enabled = False
                elif h.handler_name in (self.reading_tool | self.take_tool | self.switch):
                    h.enabled = True
            return "现在可以开始阅读！"

    def set_enable(self, enable: bool = None):
        if enable is not None:
            self.enable = enable
        else:
            self.enable = not self.enable
        handlers = star_handlers_registry.get_handlers_by_module_name(self.module_path)
        for h in handlers:
            if h.handler_name not in self.gate:
                h.enabled = self.enable
                logger.debug(f"设置工具 {h.handler_name} 状态为 {'启用' if self.enable else '禁用'}")
        if self.enable:
            self.set_tool_status("on")
        return f"{'启用' if self.enable else '禁用'} 🍅Botomato 书架！"

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