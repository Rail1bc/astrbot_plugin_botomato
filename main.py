from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from tomato_rain_api.rain_tomato_api import RainTomatoAPI


@register("astrbot_plugin_fanqie_novel", "Rail1bc", "让ai读小说，我是说让ai读，不是给你读", "0.1.0")
class FanqieNovel(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.config = config or {}
        self.api = RainTomatoAPI(
            apikey=self.config.get("rain_api_key"),
            base_url=self.config.get("novel_resource_base"),
        )

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    @filter.command("搜书")
    async def novel_search(self, event: AstrMessageEvent):
        """根据关键词搜索小说 /搜书 <关键词> [页码|0]"""
        message_str = event.message_str
        args = message_str.split()
        keywords = args[0]
        page = int(args[1]) if len(args) > 1 else 0
        list = self.api.search(keywords=keywords, page=page)
        str = "搜索结果：\n----------\n" + "\n----------\n".join([f"{i+1}. {book.book_info_to_str()}" for i, book in enumerate(list)])
        yield event.plain_result(str)

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""