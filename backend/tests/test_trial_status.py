# backend/tests/test_trial_status.py
"""trial_status 纯函数 + main 输出冒烟（试用期协议 spec §3/§7）。"""

from datetime import date, datetime, timedelta, timezone

from scripts.trial_status import (
    active_streak,
    count_entries,
    local_coverage,
    parse_friday_readings,
    to_local_date,
)

# ---- to_local_date：naive 视为 UTC（normalizeUtc 口径），aware 先转 UTC 再本地 ----


def test_to_local_date_naive_treated_as_utc():
    # 契约：naive == 按 UTC 解释（与系统时区无关的等价断言）
    naive = datetime(2026, 10, 1, 16, 0, 0)
    aware = naive.replace(tzinfo=timezone.utc)
    assert to_local_date(naive) == to_local_date(aware)


def test_to_local_date_aware_is_system_local_day():
    # 契约：aware 先归一 UTC 再转系统本地日（等价于自带 astimezone 行为）
    aware = datetime(2026, 10, 1, 16, 0, 0, tzinfo=timezone.utc)
    assert to_local_date(aware) == aware.astimezone().date()


# ---- active_streak：从 today 严格往回数 ----


def test_streak_counts_consecutive_from_today():
    today = date(2026, 10, 9)
    dates = {date(2026, 10, 9), date(2026, 10, 8), date(2026, 10, 7), date(2026, 10, 5)}
    assert active_streak(dates, today) == 3  # 10-6 断档


def test_streak_zero_when_today_inactive():
    today = date(2026, 10, 9)
    dates = {date(2026, 10, 8), date(2026, 10, 7)}
    assert active_streak(dates, today) == 0  # spec：从今天往回，今天没有即 0


def test_streak_empty():
    assert active_streak(set(), date(2026, 10, 9)) == 0


# ---- local_coverage：M2 口径，分母 0 不除零 ----


def test_coverage_normal():
    assert local_coverage(3, 10) == "3/10 (30.0%)"


def test_coverage_zero_denominator():
    assert local_coverage(0, 0) == "暂无题目"


# ---- parse_friday_readings：围栏跳过 + % 解析 ----


def test_parse_readings_from_table():
    md = (
        "## 每周五自查\n\n"
        "| 周五日期 | 覆盖率读数 | 新问题数(本周) | 本周最卡的一件事 |\n"
        "|----------|-----------|--------------|----------------|\n"
        "| 2026-10-03 | 12.5% | 2 | 知识库卡 |\n"
        "| 2026-10-10 | 18.0% | 1 | 复习队列空 |\n"
    )
    rows = parse_friday_readings(md)
    assert rows == [(date(2026, 10, 3), 12.5), (date(2026, 10, 10), 18.0)]


def test_parse_readings_skips_fenced_example():
    md = "```\n| 2026-10-03 | 99.9% | x | x |\n```\n| 2026-10-10 | 1.0% | x | x |\n"
    assert parse_friday_readings(md) == [(date(2026, 10, 10), 1.0)]


def test_parse_readings_empty_table():
    assert parse_friday_readings("## 每周五自查\n\n| 周五日期 | 覆盖率读数 |\n|---|---|\n") == []


# ---- count_entries：围栏跳过 ----


def test_count_entries_counts_live_only():
    md = (
        "- [2026-10-01] 症状A | 卡点 | ? | 高\n"
        "```text\n- [2026-10-01] 现象描述 | 卡在哪 | ? | 中\n```\n"
        "- [2026-10-02] 症状B | 卡点2 | 猜测 | 低\n"
    )
    assert count_entries(md) == 2


def test_count_entries_zero():
    assert count_entries("暂无") == 0


# ---- main 冒烟（conftest 隔离库；五项标签齐 + 不写库）


def test_main_prints_five_sections(capsys):
    from scripts.trial_status import main

    assert main() == 0
    out = capsys.readouterr().out
    for label in ("连续活跃天数", "quiz 覆盖率", "覆盖率历史读数", "错题条数", "到期卡数"):
        assert label in out, label
