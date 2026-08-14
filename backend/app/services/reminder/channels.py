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
            # S6 修复（RAG #6）：原 urlopen 未用 with，resp 可能不关闭；
            # 且未校验 ServerChan 返回的 errno，HTTP 200 但 errno!=0 仍误报成功。
            with urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            try:
                payload = _json.loads(raw)
            except (ValueError, _json.JSONDecodeError):
                # 非 JSON 响应视为失败
                return False
            # ServerChan 成功时 data.errno == 0；非 0 说明推送失败（如 key 失效、超额度）
            errno = payload.get("code", payload.get("errno"))
            if errno is not None and errno != 0:
                return False
            return True
        except Exception:
            return False


CHANNELS: dict[str, type[Channel]] = {
    "terminal": TerminalChannel,
    "serverchan": ServerChanChannel,
}
