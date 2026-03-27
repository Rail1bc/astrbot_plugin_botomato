from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .bookshelf.book import Book
from .rain_api.rain_tomato_api import RainTomatoAPI


@register("astrbot_plugin_fanqie_novel", "Rail1bc", "让ai读小说，我是说让ai读，不是给你读", "0.1.0")
class FanqieNovel(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.api: RainTomatoAPI | None = None
        self.config = config or {}

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        # 初始化 api
        apikey = self.config.get("rain_apikey")
        base_url = self.config.get("rain_api_base_url")
        if not apikey or not base_url:
            logger.warning("没有 api key 或 书源地址，无法更新、获取新的书籍信息。")
        else:
            self.api = RainTomatoAPI(apikey=apikey,base_url=base_url,)

    @filter.command("测试")
    async  def test(self, event: AstrMessageEvent):
        event.plain_result("测试成功" + event.message_str)
        event.plain_result(event.message_str.split()[0])

    @filter.command("test")
    async  def test(self, event: AstrMessageEvent):
        event.plain_result("测试成功" + event.message_str)
        event.plain_result(event.message_str.split()[0])

    @filter.command("搜书")
    async def novel_search(self, event: AstrMessageEvent):
        """根据关键词搜索小说 /搜书 <关键词> [页码|0]"""
        if not self.api_enabled():
            event.plain_result("api失效，无法更新、获取新的书籍信息。")
            return

        message_str = event.message_str
        args = message_str.split()
        keywords = args[0]
        page = int(args[1]) if len(args) > 1 else 0
        list = Book.book_list_from_dict(self.api.search(keywords=keywords, page=page))
        str = ("搜索结果：\n----------\n" +
               "\n----------\n".join([f"{i+1}. {book.book_info_to_str()}" for i, book in enumerate(list)]))
        yield event.plain_result(str)

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""

    def api_enabled(self):
        if self.api is None or self.api.enable is False:
            return False
        else:
            return True