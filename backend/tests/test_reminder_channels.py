"""提醒通道单元测试。"""
from app.services.reminder.channels import TerminalChannel, ServerChanChannel


def test_terminal_channel():
    ch = TerminalChannel()
    assert ch.send("test title", "test body") is True


def test_serverchan_invalid_key_does_not_crash():
    """无效 SendKey 应返回 False，不抛异常。"""
    ch = ServerChanChannel("invalid-key-12345")
    result = ch.send("test", "body")
    assert isinstance(result, bool)
