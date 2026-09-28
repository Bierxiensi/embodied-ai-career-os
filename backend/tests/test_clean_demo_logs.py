# backend/tests/test_clean_demo_logs.py
"""Y7 演示学习日志判定谓词测试（2026-09-24 前置裁决）。"""

from datetime import datetime

from scripts.clean_demo_learning_logs import is_demo_log


def test_demo_batch_matched():
    assert is_demo_log(
        "完成了 ROS2 publisher 节点，记录到学习日志。",
        datetime(2026, 9, 10, 7, 7, 20),
    )


def test_real_log_not_matched():
    assert not is_demo_log(
        "今天把 DPO 的 loss 推导过了一遍，弄清了 reference model 的作用。",
        datetime(2026, 9, 24, 20, 0, 0),
    )


def test_same_day_real_content_not_matched():
    # 同日但内容不含演示指纹 → 不删（宁可漏删，不可错删）
    assert not is_demo_log("手写 SFT trainer 笔记", datetime(2026, 9, 10, 23, 0, 0))
