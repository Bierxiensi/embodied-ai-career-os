"""提醒推送通道实现。

每个通道实现 send(title, body) 方法。
通道注册表 CHANNELS 按名查找，便于扩展。
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Channel(ABC):
    """推送通道抽象基类。"""

    @abstractmethod
    def send(self, title: str, body: str) -> bool:
        """发送推送。成功返回 True，失败返回 False。"""
        ...


class TerminalChannel(Channel):
    """终端打印通道（开发调试默认）。"""

    def send(self, title: str, body: str) -> bool:
        print(f"\n{'='*50}")
        print(f"📬 {title}")
        print(f"{'='*50}")
        print(body)
        print(f"{'='*50}\n")
        return True


class ServerChanChannel(Channel):
    """Server酱微信推送通道。

    注册地址: https://sct.ftqq.com/
    免费额度: 每天 5 条
    """

    def __init__(self, send_key: str):
        self._send_key = send_key.strip()

    def send(self, title: str, body: str) -> bool:
        import json as _json
        from urllib.request import Request, urlopen

        url = f"https://sctapi.ftqq.com/{self._send_key}.send"
        data = _json.dumps({"title": title, "desp": body}).encode("utf-8")
        try:
            req = Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
            )
            urlopen(req, timeout=10)
            return True
        except Exception:
            return False


CHANNELS: dict[str, type[Channel]] = {
    "terminal": TerminalChannel,
    "serverchan": ServerChanChannel,
}
