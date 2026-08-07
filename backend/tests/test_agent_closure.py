"""Embodied AI Career OS · Day6 Agent 闭环稳定性测试套件。

覆盖维度：
  1. 功能测试：Planner 正常生成 + 持久化 + agent_runs 记录
  2. 边界测试：空 skills / 极端时长 / current_focus / 未知技能 / energy_level
  3. 数据一致性：tasks ↔ agent_runs 对应关系
  4. 状态机：Task todo → doing → done 流转
  5. 稳定性：连续调用 + 并发调用
  6. 错误处理：persist=false / 字段缺失 / 422 校验

执行方式：
    cd backend && python tests/test_agent_closure.py

输出：结构化测试结果（PASS/FAIL/SKIP + 详情），并写入 reports/ 目录。
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests

# ===== 配置 =====
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
DB_PATH = os.environ.get("DB_PATH", "data/app.db")
REPORT_DIR = "reports"

# 复用项目根目录的 DB（脚本从 backend/ 目录运行）
if not os.path.exists(DB_PATH):
    DB_PATH = "/workspace/embodied-ai-career-os/backend/data/app.db"


# ===== 测试结果收集 =====
class TestResult:
    """单个测试用例结果。"""

    def __init__(self, suite: str, case_id: str, name: str):
        self.suite = suite
        self.case_id = case_id
        self.name = name
        self.status: str = "RUN"  # PASS / FAIL / SKIP
        self.detail: str = ""
        self.elapsed_ms: int = 0
        self.evidence: dict = {}  # 证据数据（请求/响应/DB 状态）

    def to_dict(self) -> dict:
        return {
            "suite": self.suite,
            "case_id": self.case_id,
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "elapsed_ms": self.elapsed_ms,
            "evidence": self.evidence,
        }


results: list[TestResult] = []


def record(suite: str, case_id: str, name: str):
    """注册一个测试用例（用作装饰器或手动调用）。"""

    r = TestResult(suite, case_id, name)
    results.append(r)
    return r


def run_case(suite: str, case_id: str, name: str, fn):
    """执行单个测试用例，捕获异常并记录耗时。"""

    r = record(suite, case_id, name)
    start = time.perf_counter()
    try:
        fn(r)
        if r.status == "RUN":
            r.status = "PASS"
    except AssertionError as e:
        r.status = "FAIL"
        r.detail = f"AssertionError: {e}"
    except Exception as e:  # noqa: BLE001
        r.status = "FAIL"
        r.detail = f"{type(e).__name__}: {e}"
    r.elapsed_ms = int((time.perf_counter() - start) * 1000)
    return r


# ===== 工具函数 =====
def call_planner(payload: dict) -> requests.Response:
    """调用 Planner API。"""

    return requests.post(
        f"{BACKEND_URL}/api/planner/generate",
        json=payload,
        timeout=10,
    )


def db_query(sql: str, params: tuple = ()) -> list[tuple]:
    """执行只读 SQL 查询。"""

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()


def count_agent_runs() -> int:
    return db_query("SELECT COUNT(*) FROM agent_runs")[0][0]


def count_tasks() -> int:
    return db_query("SELECT COUNT(*) FROM tasks")[0][0]


# ============================================================
# 测试套件 1：功能测试
# ============================================================
def test_functional():
    suite = "功能测试"

    # F-01: 正常生成任务（最大缺口 Isaac）
    def f01(r: TestResult):
        before_runs = count_agent_runs()
        before_tasks = count_tasks()
        resp = call_planner({
            "available_minutes": 45,
            "target_role": "Robot AI Engineer",
            "skills": [
                {"name": "Isaac", "level": 0, "target": 4},
                {"name": "ROS2", "level": 1, "target": 4},
            ],
            "energy_level": "normal",
            "persist": True,
        })
        assert resp.status_code == 200, f"HTTP {resp.status_code}"
        body = resp.json()
        assert body["success"] is True, "success=false"
        data = body["data"]
        # 验证：选中最大缺口 Isaac
        assert data["skill"] == "Isaac", f"skill={data['skill']}"
        assert data["task_id"] is not None, "task_id 为空（未持久化）"
        assert data["status"] == "todo"
        assert len(data["acceptance"]) >= 1, "验收标准为空"
        r.evidence = {
            "selected_skill": data["skill"],
            "task_id": data["task_id"],
            "title": data["title"],
            "duration": data["duration"],
        }
        # 验证 DB：agent_runs +1, tasks +1
        assert count_agent_runs() == before_runs + 1, "agent_runs 未增加"
        assert count_tasks() == before_tasks + 1, "tasks 未增加"

    run_case(suite, "F-01", "正常生成任务（Isaac 最大缺口）+ 持久化 + agent_runs", f01)

    # F-02: current_focus 强制聚焦（覆盖自动选择分支）
    def f02(r: TestResult):
        resp = call_planner({
            "available_minutes": 30,
            "skills": [
                {"name": "Isaac", "level": 0, "target": 4},
                {"name": "ROS2", "level": 1, "target": 4},
            ],
            "current_focus": "ROS2",  # 强制聚焦 ROS2 而非 Isaac
            "persist": False,
        })
        data = resp.json()["data"]
        assert data["skill"] == "ROS2", f"current_focus 未生效, skill={data['skill']}"
        r.evidence = {"forced_skill": data["skill"]}

    run_case(suite, "F-02", "current_focus 强制聚焦技能（覆盖自动选择）", f02)

    # F-03: agent_runs 记录内容完整性（input + output）
    def f03(r: TestResult):
        rows = db_query(
            "SELECT agent_name, input_context, output_result FROM agent_runs "
            "ORDER BY created_at DESC LIMIT 1"
        )
        assert rows, "agent_runs 表为空"
        agent_name, input_json, output_json = rows[0]
        assert agent_name == "planner", f"agent_name={agent_name}"
        input_data = json.loads(input_json)
        output_data = json.loads(output_json)
        assert "skills" in input_data, "input 缺少 skills"
        assert "available_minutes" in input_data, "input 缺少 available_minutes"
        assert "title" in output_data, "output 缺少 title"
        assert "skill" in output_data, "output 缺少 skill"
        r.evidence = {
            "input_keys": list(input_data.keys()),
            "output_keys": list(output_data.keys()),
        }

    run_case(suite, "F-03", "agent_runs 记录内容完整性（input + output JSON）", f03)


# ============================================================
# 测试套件 2：边界测试
# ============================================================
def test_boundary():
    suite = "边界测试"

    # B-01: 空 skills 列表 → selected_skill="Unknown" → fallback 任务
    def b01(r: TestResult):
        resp = call_planner({
            "available_minutes": 30,
            "skills": [],
            "persist": False,
        })
        data = resp.json()["data"]
        # Unknown 无模板 → fallback 通用任务
        assert data["skill"] == "Unknown", f"skill={data['skill']}"
        assert "Unknown" in data["title"], f"title={data['title']}"
        assert data["difficulty"] == "beginner", "fallback 应为 beginner"
        r.evidence = {"title": data["title"], "skill": data["skill"]}

    run_case(suite, "B-01", "空 skills 列表 → fallback 通用任务", b01)

    # B-02: 未知技能（无模板）→ fallback
    def b02(r: TestResult):
        resp = call_planner({
            "available_minutes": 40,
            "skills": [{"name": "QuantumComputing", "level": 0, "target": 5}],
            "persist": False,
        })
        data = resp.json()["data"]
        assert data["skill"] == "QuantumComputing"
        assert "QuantumComputing" in data["title"], "fallback 标题未含技能名"
        assert len(data["acceptance"]) == 3, "fallback 验收项应为 3 条"
        r.evidence = {"title": data["title"], "acceptance_count": len(data["acceptance"])}

    run_case(suite, "B-02", "未知技能（无模板）→ fallback 通用任务", b02)

    # B-03: 极端时长 available_minutes=5（最小值）
    def b03(r: TestResult):
        resp = call_planner({
            "available_minutes": 5,
            "skills": [{"name": "Isaac", "level": 0, "target": 4}],
            "persist": False,
        })
        data = resp.json()["data"]
        # 时长截断：min(5, 60) = 5
        assert data["duration"] == 5, f"duration={data['duration']}"
        r.evidence = {"duration": data["duration"]}

    run_case(suite, "B-03", "极端时长 available_minutes=5（最小值截断）", b03)

    # B-04: 极端时长 available_minutes=480（最大值）
    def b04(r: TestResult):
        resp = call_planner({
            "available_minutes": 480,
            "skills": [{"name": "Isaac", "level": 0, "target": 4}],
            "persist": False,
        })
        data = resp.json()["data"]
        # 模板基准 60 < 480，应取 60
        assert data["duration"] == 60, f"duration={data['duration']}"
        r.evidence = {"duration": data["duration"], "base_minutes": 60}

    run_case(suite, "B-04", "极端时长 available_minutes=480（取模板基准）", b04)

    # B-05: energy_level=low → beginner 难度
    def b05(r: TestResult):
        resp = call_planner({
            "available_minutes": 60,
            "skills": [{"name": "VLA", "level": 0, "target": 4}],
            "energy_level": "low",
            "persist": False,
        })
        data = resp.json()["data"]
        assert data["difficulty"] == "beginner", f"difficulty={data['difficulty']}"
        r.evidence = {"difficulty": data["difficulty"]}

    run_case(suite, "B-05", "energy_level=low → beginner 难度", b05)

    # B-06: energy_level=high → intermediate 难度
    def b06(r: TestResult):
        resp = call_planner({
            "available_minutes": 90,
            "skills": [{"name": "VLA", "level": 0, "target": 4}],
            "energy_level": "high",
            "persist": False,
        })
        data = resp.json()["data"]
        assert data["difficulty"] == "intermediate", f"difficulty={data['difficulty']}"
        r.evidence = {"difficulty": data["difficulty"]}

    run_case(suite, "B-06", "energy_level=high → intermediate 难度", b06)

    # B-07: gap 相同时 level 低的优先（排序稳定性）
    def b07(r: TestResult):
        resp = call_planner({
            "available_minutes": 30,
            "skills": [
                {"name": "VLA", "level": 2, "target": 4},  # gap=2, level=2
                {"name": "ROS2", "level": 1, "target": 3},  # gap=2, level=1（更弱）
            ],
            "persist": False,
        })
        data = resp.json()["data"]
        # gap 相同，level 低的优先 → ROS2
        assert data["skill"] == "ROS2", f"排序错误, skill={data['skill']}"
        r.evidence = {"selected": data["skill"], "reason": "gap 相同时 level 低的优先"}

    run_case(suite, "B-07", "gap 相同时 level 低的优先（排序稳定性）", b07)


# ============================================================
# 测试套件 3：数据一致性测试
# ============================================================
def test_consistency():
    suite = "数据一致性测试"

    # C-01: 持久化的 task 字段与 Planner 输出一致
    def c01(r: TestResult):
        resp = call_planner({
            "available_minutes": 45,
            "skills": [{"name": "ROS2", "level": 1, "target": 4}],
            "persist": True,
        })
        data = resp.json()["data"]
        task_id = data["task_id"]
        rows = db_query(
            "SELECT title, skill_name, duration, difficulty, status, acceptance, resources "
            "FROM tasks WHERE id = ?",
            (task_id,),
        )
        assert rows, f"tasks 表无 id={task_id}"
        title, skill_name, duration, difficulty, status, acc_json, res_json = rows[0]
        assert title == data["title"], f"title 不一致: {title} vs {data['title']}"
        assert skill_name == data["skill"], f"skill 不一致"
        assert duration == data["duration"], f"duration 不一致"
        assert difficulty == data["difficulty"], f"difficulty 不一致"
        assert status == data["status"], f"status 不一致"
        assert json.loads(acc_json) == data["acceptance"], "acceptance 不一致"
        assert json.loads(res_json) == data["resources"], "resources 不一致"
        r.evidence = {"task_id": task_id, "all_fields_match": True}

    run_case(suite, "C-01", "持久化 task 字段与 Planner 输出完全一致", c01)

    # C-02: agent_runs input/output 与实际请求/响应对应
    def c02(r: TestResult):
        payload = {
            "available_minutes": 35,
            "skills": [{"name": "Isaac", "level": 0, "target": 4}],
            "energy_level": "high",
            "persist": True,
        }
        resp = call_planner(payload)
        data = resp.json()["data"]
        rows = db_query(
            "SELECT input_context, output_result FROM agent_runs "
            "ORDER BY created_at DESC LIMIT 1"
        )
        input_data = json.loads(rows[0][0])
        output_data = json.loads(rows[0][1])
        # input 应含本次请求关键字段
        assert input_data["available_minutes"] == 35
        assert input_data["energy_level"] == "high"
        # output 应含生成任务
        assert output_data["title"] == data["title"]
        r.evidence = {"input_match": True, "output_match": True}

    run_case(suite, "C-02", "agent_runs input/output 与请求/响应对应", c02)

    # C-03: persist=False 时 tasks 不增加，agent_runs 仍记录
    def c03(r: TestResult):
        before_tasks = count_tasks()
        before_runs = count_agent_runs()
        call_planner({
            "available_minutes": 30,
            "skills": [{"name": "VLA", "level": 0, "target": 4}],
            "persist": False,
        })
        assert count_tasks() == before_tasks, "persist=False 时 tasks 不应增加"
        assert count_agent_runs() == before_runs + 1, "agent_runs 应仍记录"
        r.evidence = {
            "tasks_delta": 0,
            "agent_runs_delta": 1,
            "note": "persist=False 仅跳过持久化，决策仍记录",
        }

    run_case(suite, "C-03", "persist=False 时 tasks 不变 + agent_runs 仍记录", c03)


# ============================================================
# 测试套件 4：Task 状态机测试
# ============================================================
def test_state_machine():
    suite = "Task 状态机测试"

    # S-01: todo → doing → done 完整流转
    def s01(r: TestResult):
        # 1. 创建任务（Planner 生成）
        resp = call_planner({
            "available_minutes": 40,
            "skills": [{"name": "PyTorch", "level": 3, "target": 4}],
            "persist": True,
        })
        task_id = resp.json()["data"]["task_id"]
        assert task_id, "未拿到 task_id"

        # 2. 验证初始状态 todo
        rows = db_query("SELECT status FROM tasks WHERE id = ?", (task_id,))
        assert rows[0][0] == "todo", f"初始状态={rows[0][0]}"

        # 3. todo → doing
        resp = requests.patch(
            f"{BACKEND_URL}/api/tasks/{task_id}/status",
            json={"status": "doing"},
            timeout=10,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "doing"

        # 4. doing → done
        resp = requests.patch(
            f"{BACKEND_URL}/api/tasks/{task_id}/status",
            json={"status": "done"},
            timeout=10,
        )
        assert resp.json()["data"]["status"] == "done"

        # 5. DB 确认
        rows = db_query("SELECT status FROM tasks WHERE id = ?", (task_id,))
        assert rows[0][0] == "done"
        r.evidence = {"task_id": task_id, "flow": "todo → doing → done ✓"}

    run_case(suite, "S-01", "Task 状态机 todo → doing → done 完整流转", s01)

    # S-02: 非法状态被拒（422）
    def s02(r: TestResult):
        # 先建一个任务
        resp = call_planner({
            "available_minutes": 30,
            "skills": [{"name": "Python", "level": 4, "target": 5}],
            "persist": True,
        })
        task_id = resp.json()["data"]["task_id"]
        # 尝试非法状态
        resp = requests.patch(
            f"{BACKEND_URL}/api/tasks/{task_id}/status",
            json={"status": "cancelled"},  # 非法
            timeout=10,
        )
        assert resp.status_code == 422, f"应返回 422, 实际 {resp.status_code}"
        r.evidence = {"illegal_status": "cancelled", "http": 422}

    run_case(suite, "S-02", "非法状态 cancelled 被 422 拒绝", s02)


# ============================================================
# 测试套件 5：稳定性测试
# ============================================================
def test_stability():
    suite = "稳定性测试"

    # ST-01: 连续 5 次调用全部成功
    def st01(r: TestResult):
        success_count = 0
        for i in range(5):
            resp = call_planner({
                "available_minutes": 30 + i * 5,
                "skills": [{"name": "Isaac", "level": 0, "target": 4}],
                "persist": False,
            })
            if resp.status_code == 200 and resp.json()["success"]:
                success_count += 1
        assert success_count == 5, f"仅 {success_count}/5 成功"
        r.evidence = {"success": "5/5"}

    run_case(suite, "ST-01", "连续 5 次调用全部成功", st01)

    # ST-02: 并发 5 个请求（线程池）全部成功
    def st02(r: TestResult):
        def single_call(i: int) -> bool:
            try:
                resp = call_planner({
                    "available_minutes": 30,
                    "skills": [{"name": "VLA", "level": 0, "target": 4}],
                    "persist": False,
                })
                return resp.status_code == 200 and resp.json()["success"]
            except Exception:  # noqa: BLE001
                return False

        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = [ex.submit(single_call, i) for i in range(5)]
            results_list = [f.result() for f in as_completed(futures)]
        success = sum(results_list)
        assert success == 5, f"并发仅 {success}/5 成功"
        r.evidence = {"concurrent_success": "5/5"}

    run_case(suite, "ST-02", "并发 5 个请求（线程池）全部成功", st02)

    # ST-03: 响应时间 < 2s（单次）
    def st03(r: TestResult):
        start = time.perf_counter()
        resp = call_planner({
            "available_minutes": 45,
            "skills": [{"name": "Isaac", "level": 0, "target": 4}],
            "persist": False,
        })
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        assert elapsed < 2.0, f"响应时间 {elapsed:.2f}s 超过 2s 阈值"
        r.evidence = {"elapsed_s": round(elapsed, 3)}

    run_case(suite, "ST-03", "单次响应时间 < 2s", st03)


# ============================================================
# 测试套件 6：错误处理测试
# ============================================================
def test_error_handling():
    suite = "错误处理测试"

    # E-01: 缺少必填字段 skills → 422
    def e01(r: TestResult):
        resp = call_planner({"available_minutes": 30})  # 缺 skills
        assert resp.status_code == 422, f"应 422, 实际 {resp.status_code}"
        r.evidence = {"http": 422, "missing": "skills"}

    run_case(suite, "E-01", "缺少必填字段 skills → 422", e01)

    # E-02: available_minutes 超范围（< 5）→ 422
    def e02(r: TestResult):
        resp = call_planner({
            "available_minutes": 1,  # < 5
            "skills": [{"name": "Isaac", "level": 0, "target": 4}],
        })
        assert resp.status_code == 422
        r.evidence = {"http": 422, "invalid_value": 1}

    run_case(suite, "E-02", "available_minutes=1 超范围 → 422", e02)

    # E-03: available_minutes 超范围（> 480）→ 422
    def e03(r: TestResult):
        resp = call_planner({
            "available_minutes": 500,  # > 480
            "skills": [{"name": "Isaac", "level": 0, "target": 4}],
        })
        assert resp.status_code == 422
        r.evidence = {"http": 422, "invalid_value": 500}

    run_case(suite, "E-03", "available_minutes=500 超范围 → 422", e03)

    # E-04: skill level 超范围（> 5）→ 422
    def e04(r: TestResult):
        resp = call_planner({
            "available_minutes": 30,
            "skills": [{"name": "Isaac", "level": 6, "target": 4}],  # level > 5
        })
        assert resp.status_code == 422
        r.evidence = {"http": 422, "invalid_level": 6}

    run_case(suite, "E-04", "skill level=6 超范围 → 422", e04)

    # E-05: 不存在的 task_id 状态更新 → 404
    def e05(r: TestResult):
        resp = requests.patch(
            f"{BACKEND_URL}/api/tasks/999999/status",
            json={"status": "doing"},
            timeout=10,
        )
        assert resp.status_code == 404, f"应 404, 实际 {resp.status_code}"
        r.evidence = {"http": 404, "task_id": 999999}

    run_case(suite, "E-05", "不存在的 task_id 状态更新 → 404", e05)


# ============================================================
# 测试套件 7：CRUD 端点基础验证（Day6 API 范围）
# ============================================================
def test_crud_endpoints():
    suite = "CRUD 端点测试"

    # A-01: GET /api/career 返回结构
    def a01(r: TestResult):
        resp = requests.get(f"{BACKEND_URL}/api/career", timeout=10)
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "target_role" in data
        assert "salary_target" in data
        r.evidence = {"target_role": data["target_role"]}

    run_case(suite, "A-01", "GET /api/career 返回正确结构", a01)

    # A-02: GET /api/skills 返回列表
    def a02(r: TestResult):
        resp = requests.get(f"{BACKEND_URL}/api/skills", timeout=10)
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 10, f"技能数 {len(data)} < 10"
        r.evidence = {"skills_count": len(data)}

    run_case(suite, "A-02", "GET /api/skills 返回技能列表（≥10）", a02)

    # A-03: GET /api/tasks 返回列表
    def a03(r: TestResult):
        resp = requests.get(f"{BACKEND_URL}/api/tasks", timeout=10)
        data = resp.json()["data"]
        assert isinstance(data, list)
        r.evidence = {"tasks_count": len(data)}

    run_case(suite, "A-03", "GET /api/tasks 返回任务列表", a03)

    # A-04: PATCH /api/skills/{id} 更新等级
    def a04(r: TestResult):
        # 取第一个技能
        skills = requests.get(f"{BACKEND_URL}/api/skills", timeout=10).json()["data"]
        sid = skills[0]["id"]
        original_level = skills[0]["level"]
        new_level = max(0, original_level - 1) if original_level == 5 else original_level + 1
        resp = requests.patch(
            f"{BACKEND_URL}/api/skills/{sid}",
            json={"level": new_level},
            timeout=10,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["level"] == new_level
        # 恢复原值（避免污染种子数据）
        requests.patch(
            f"{BACKEND_URL}/api/skills/{sid}",
            json={"level": original_level},
            timeout=10,
        )
        r.evidence = {"skill_id": sid, "temp_level": new_level, "restored": True}

    run_case(suite, "A-04", "PATCH /api/skills/{id} 更新等级 + 恢复", a04)


# ============================================================
# 报告生成
# ============================================================
def generate_report():
    """生成结构化测试报告。"""

    os.makedirs(REPORT_DIR, exist_ok=True)
    total = len(results)
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    skipped = sum(1 for r in results if r.status == "SKIP")
    pass_rate = (passed / total * 100) if total else 0

    # 按套件分组统计
    suites: dict[str, dict] = {}
    for r in results:
        if r.suite not in suites:
            suites[r.suite] = {"total": 0, "pass": 0, "fail": 0}
        suites[r.suite]["total"] += 1
        if r.status == "PASS":
            suites[r.suite]["pass"] += 1
        elif r.status == "FAIL":
            suites[r.suite]["fail"] += 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 控制台输出
    print("\n" + "=" * 70)
    print("  Embodied AI Career OS · Day6 Agent 闭环稳定性测试报告")
    print("=" * 70)
    print(f"  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  后端地址: {BACKEND_URL}")
    print(f"  数据库:   {DB_PATH}")
    print(f"  用例总数: {total}    通过: {passed}    失败: {failed}    跳过: {skipped}")
    print(f"  通过率:   {pass_rate:.1f}%")
    print("-" * 70)
    print("  按套件统计:")
    for name, s in suites.items():
        rate = s["pass"] / s["total"] * 100
        print(f"    {name:<20} {s['pass']}/{s['total']}  ({rate:.0f}%)")
    print("-" * 70)
    print("  详细结果:")
    for r in results:
        icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "—"}.get(r.status, "?")
        print(f"    {icon} [{r.case_id}] {r.name}  ({r.elapsed_ms}ms)")
        if r.status == "FAIL":
            print(f"        └─ {r.detail}")
        elif r.evidence:
            ev = json.dumps(r.evidence, ensure_ascii=False)
            if len(ev) > 100:
                ev = ev[:97] + "..."
            print(f"        └─ {ev}")
    print("=" * 70)

    # JSON 报告
    report_data = {
        "title": "Embodied AI Career OS · Day6 Agent 闭环稳定性测试报告",
        "timestamp": datetime.now().isoformat(),
        "backend_url": BACKEND_URL,
        "db_path": DB_PATH,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": round(pass_rate, 2),
        },
        "suites": suites,
        "cases": [r.to_dict() for r in results],
    }
    json_path = os.path.join(REPORT_DIR, f"day6_agent_test_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"\n  JSON 报告已写入: {json_path}")

    return passed, failed, json_path


# ============================================================
# 主入口
# ============================================================
def main():
    # 预检：后端可达性
    print("预检：后端服务连通性...")
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if r.status_code != 200:
            print(f"✗ 后端健康检查失败: HTTP {r.status_code}")
            sys.exit(1)
        print(f"✓ 后端可达: {r.json()}")
    except Exception as e:  # noqa: BLE001
        print(f"✗ 后端不可达: {e}")
        print(f"  请确认后端已启动：cd backend && uvicorn app.main:app --port 8000")
        sys.exit(1)

    # 预检：数据库可达性
    if not os.path.exists(DB_PATH):
        print(f"✗ 数据库不存在: {DB_PATH}")
        sys.exit(1)
    print(f"✓ 数据库可达: {DB_PATH}")
    print()

    # 记录测试前基线
    baseline = {"agent_runs": count_agent_runs(), "tasks": count_tasks()}
    print(f"测试前基线: agent_runs={baseline['agent_runs']}, tasks={baseline['tasks']}")
    print()

    # 执行所有套件
    print("开始执行测试套件...\n")
    test_functional()
    test_boundary()
    test_consistency()
    test_state_machine()
    test_stability()
    test_error_handling()
    test_crud_endpoints()

    # 生成报告
    passed, failed, json_path = generate_report()

    # 退出码：有失败返回 1
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
