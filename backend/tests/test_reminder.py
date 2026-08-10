"""Reminder 引擎测试（Terminal 通道）。"""
import pytest
from app.services.reminder.engine import ReminderEngine
from app.services.reminder.templates import (
    morning_template,
    evening_template,
    comeback_template,
)


def test_morning_template_output():
    title, body = morning_template(
        task_title="ROS2 publisher 实战",
        skill_name="ROS2",
        current_level=1,
        target_level=4,
        duration=40,
    )
    assert "ROS2 publisher" in title or "ROS2 publisher" in body
    assert "40" in body


def test_evening_template_output():
    title, body = evening_template("ROS2 publisher 实战", "ROS2")
    assert "1" in body
    assert "2" in body
    assert "3" in body


def test_comeback_template_output():
    title, body = comeback_template(3, "ROS2 publisher", "ROS2", "继续 subscriber")
    assert "3" in title
    assert "ROS2" in body


def test_engine_terminal_channel():
    """Terminal 通道 send 永远返回 True。"""
    engine = ReminderEngine()
    assert engine.send_morning() is True
    assert engine.send_evening() is True
