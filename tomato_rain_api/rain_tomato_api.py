import requests
import time
import logging
from urllib.parse import urlencode, urlparse, parse_qs

logger = logging.getLogger(__name__)

class RainTomatoAPI:
    # 默认 base 地址
    DEFAULT_BASE = 'https://v3.rain.ink/fanqie/'

    def __init__(self, apikey: str, base_url: str = None, timeout: int = 10, max_retries: int = 2, backoff: float = 0.3):
        """初始化客户端。

        参数:
            apikey: 必需，访问网关的 API key。
            base_url: 可选，自定义基地址（覆盖默认 DEFAULT_BASE）。
            timeout: 请求超时时间（秒）。
            max_retries: 发生请求异常时的最大重试次数（不包含首次尝试）。
            backoff: 重试回退基数，用于指数退避（sleep = backoff * attempt）。

        异常:
            若未提供 apikey，则抛出 ValueError。
        """
        if not apikey:
            raise ValueError("没有apikey")
        self.apikey = apikey
        self.base_url = base_url or RainTomatoAPI.DEFAULT_BASE
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        # 使用 requests.Session 复用连接
        self.session = requests.Session()
        # 默认请求头
        self.session.headers.update({
            "User-Agent": "tomato-rain-client/1.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        })

    # 将搜索 / 书籍信息 / 目录 / 章节作为类方法
    def search(self, keywords: str, page: int = 0):
        """按关键词搜索书籍。

        参数:
            keywords: 搜索关键字。
            page: 可选，页码（默认为 0）。

        返回值: 解析后的 JSON（列表或字典）或 None。
        """
        params = {'type': 1, 'keywords': keywords, 'page': page}
        return self._get(params)

    def book_info(self, bookid: str):
        """获取书籍信息。

        参数:
            bookid: 书籍 ID 或标识。

        返回值: 书籍信息的解析后的 JSON 或 None。
        """
        params = {'type': 2, 'bookid': bookid}
        return self._get(params)

    def toc(self, bookid: str):
        """获取书籍目录（章节列表）。

        参数:
            bookid: 书籍 ID。

        返回值: 目录的解析后的 JSON 或 None。
        """
        params = {'type': 3, 'bookid': bookid}
        return self._get(params)

    def chapter(self, itemid: str, tone: dict = None):
        """获取章节内容。

        参数:
            itemid: 章节或条目的 ID。
            tone: 可选，字典形式的额外查询参数，例如 {'tone_id': '74'}。

        返回值: 章节内容的解析后的 JSON，或纯文本，或 None（视网关返回而定）。
        """
        params = {'type': 4, 'itemid': itemid}
        if tone and isinstance(tone, dict):
            params.update(tone)
        return self._get(params)

    def _get(self, params: dict, base_override: str = None):
        """内部通用 GET 请求构建与执行函数。

        行为说明：
            - 将客户端的 apikey 注入到查询参数（如果 params 中未包含 apikey）。
            - 使用 client.base_url（或 base_override）构建最终的请求 URL。
            - 支持重复尝试请求（基于 max_retries）并进行指数退避。
            - 若响应 body 为空或为字符串 'null'，返回 None；若响应不是 JSON，返回原始文本。
        参数:
            params: 要附加到查询字符串的参数字典。
            base_override: 可选，用以覆盖 client.base_url 的基地址（例如直接使用导入配置中的模板）。

        返回值:
            - 成功时返回解析后的 JSON（dict 或 list）或原始文本；
            - 对于显式的空/ null 响应返回 None；
            - 在超出重试次数并发生请求异常时抛出最后一次的 RequestException。
        """
        params = params.copy()
        # 如果 params 中没有 apikey，则注入客户端的 apikey
        if 'apikey' not in params:
            params['apikey'] = self.apikey
        base = base_override or self.base_url
        # 构建 URL：如果 base 已经包含 '?'，则使用 '&' 连接，否则使用 '?'
        url = base
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}{urlencode(params)}"
        last_err = None
        # total attempts = 1 + max_retries
        for attempt in range(1, self.max_retries + 2):
            try:
                resp = self.session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                # 响应可能为空或为字符串 'null'，在这些情况下统一返回 None
                if not resp.text or resp.text.strip() == 'null':
                    return None
                try:
                    # 优先尝试解析为 JSON
                    return resp.json()
                except ValueError:
                    # 如果不是 JSON，则返回原始文本（例如纯文本章节内容）
                    return resp.text
            except requests.RequestException as e:
                # 记录最后一个错误并在下一次重试前等待
                last_err = e
                logger.debug('Request failed attempt %s: %s', attempt, e)
                time.sleep(self.backoff * attempt)
        # 超出重试次数后抛出最后一次捕获的异常
        raise last_err


    def load_import_config(self, import_url: str, timeout: int = None):
        """从导入配置 URL 获取配置并尝试提取 `bookSourceUrl`。

        该方法会将 client 的 base_url 更新为配置中发现的 `bookSourceUrl`（如果存在）。

        返回值:
            - 成功时返回解析后的 JSON（通常为 list 或 dict）；
            - 失败或网关返回 `null` 时返回 None。

        参数:
            import_url: 导入配置的 URL（必需）。
            timeout: 可选的超时时间，若未指定则使用客户端的默认 timeout。
        """
        if not import_url:
            raise ValueError("没有import_url")
        t = timeout or self.timeout

        try:
            r = self.session.get(import_url, timeout=t)
            r.raise_for_status()
            if not r.text or r.text.strip() == 'null':
                logger.warning("导入配置失败，网关返回无效响应")
                return None
            cfg = r.json()
            # 期望 cfg 是一个列表；列表第一个元素可能包含 bookSourceUrl
            if isinstance(cfg, list) and len(cfg) > 0 and isinstance(cfg[0], dict):
                # 优先尝试 bookSourceUrl，再尝试 sourceUrl
                bs = cfg[0].get('bookSourceUrl') or cfg[0].get('sourceUrl')
                if bs:
                    # 规范化：提取 scheme://netloc/path 作为 base
                    parsed = urlparse(bs)
                    base_candidate = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    qs = parse_qs(parsed.query)
                    if 'apikey' in qs:
                        # 如果模板中包含 apikey，则覆盖客户端的 apikey
                        self.apikey = qs['apikey'][0]
                        # 保留完整的模板 URL 当作 base_url
                        self.base_url = bs
                    else:
                        self.base_url = base_candidate
                    logger.info('Set client base_url to %s', self.base_url)
            return cfg
        except requests.RequestException as e:
            logger.debug('加载配置失败: %s', e)
            return None

