"""Embodied AI Career OS · Day7 Learning Loop 全链路 E2E 测试。

用户故事场景模拟：
    一位 Robot AI Engineer 转型候选人「今天一天的学习流程」：
    1. 打开 Dashboard，查看当前技能缺口
    2. 调用 Planner 生成今日 3 个任务（Isaac/ROS2/VLA）
    3. 逐一执行学习，产出不同质量的学习证据（充分/部分/不足）
    4. 逐一提交复盘，触发 Reviewer 评估
    5. 验证技能等级、evidence、agent_runs 全部正确更新
    6. Dashboard 反射：新技能等级在 API 可见
    7. Planner 下次决策受学习结果影响

覆盖维度：
    - Planner → Task → LearningLog → Reviewer → SkillAssessment → Skill Update → Dashboard 反射

执行方式：
    cd backend && python tests/test_e2e_learning_loop.py
    # 可选：不重置数据库（保留开发数据）
    E2E_RESET_DB=0 python tests/test_e2e_learning_loop.py
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime

import requests

# ===== 配置 =====
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
DB_PATH = "/workspace/embodied-ai-career-os/backend/data/app.db"
REPORT_DIR = "/workspace/embodied-ai-career-os/backend/reports"
RESET_DB = os.environ.get("E2E_RESET_DB", "1") == "1"


# ================================================================
# 测试基础设施
# ================================================================

class E2ETest:
    """E2E 测试结果收集器，按场景步骤记录。"""

    def __init__(self):
        self.steps: list[dict] = []
        self.start_time = time.perf_counter()

    def step(self, section: str, description: str):
        self.steps.append({
            "section": section,
            "description": description,
            "status": "RUNNING",
            "start": time.perf_counter(),
            "checks": [],
        })
        n = len(self.steps)
        print(f"\n{'='*60}")
        print(f"  Step {n}: [{section}] {description}")
        print(f"{'='*60}")

    def check(self, name: str, cond: bool, detail: str = ""):
        step = self.steps[-1]
        step["checks"].append({"name": name, "ok": bool(cond), "detail": detail})
        icon = "✓" if cond else "✗"
        d = f" — {detail}" if detail else ""
        print(f"    {icon} {name}{d}")

    def ok(self):
        s = self.steps[-1]
        s["status"] = "PASS"
        s["elapsed_ms"] = int((time.perf_counter() - s["start"]) * 1000)

    def fail(self, detail: str = ""):
        s = self.steps[-1]
        s["status"] = "FAIL"
        s["elapsed_ms"] = int((time.perf_counter() - s["start"]) * 1000)
        s["fail_reason"] = detail
        print(f"    ✗ FAIL: {detail}")


# ===== DB 辅助 =====

def db_query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return conn.cursor().execute(sql, params).fetchall()
    finally:
        conn.close()


def db_count(table: str, where: str = "1=1") -> int:
    return db_query(f"SELECT COUNT(*) AS c FROM {table} WHERE {where}")[0]["c"]


def _skill_row_to_dict(row: sqlite3.Row) -> dict:
    """SQLite JSON 字段（evidence）是字符串，需 json.loads 转为数组，
       否则 len() 取的是字符串长度，会与 API 返回的数组长度不一致。
    """
    d = dict(row)
    for k in ("evidence", "acceptance", "resources"):
        if k in d and d[k] and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except Exception:
                pass
        if k in d and d[k] is None:
            d[k] = []
    return d


def get_skill(name: str) -> dict | None:
    rows = db_query("SELECT * FROM skills WHERE name = ?", (name,))
    return _skill_row_to_dict(rows[0]) if rows else None


def get_skill_by_id(skill_id: int) -> dict | None:
    rows = db_query("SELECT * FROM skills WHERE id = ?", (skill_id,))
    return _skill_row_to_dict(rows[0]) if rows else None


# ===== 后端 & DB 重置 =====

def wait_backend(timeout: int = 60) -> bool:
    for _ in range(timeout):
        try:
            if requests.get(f"{BACKEND_URL}/health", timeout=2).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def reset_backend_and_db() -> bool:
    print("[准备] 检查后端健康检查...")
    try:
        requests.get(f"{BACKEND_URL}/health", timeout=5)
    except Exception as e:
        print(f"  ✗ 后端不可达: {e}")
        return False

    if not RESET_DB:
        print("  E2E_RESET_DB=0，跳过 DB 重置")
        return True

    # 备份
    if os.path.exists(DB_PATH):
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        backup = f"{DB_PATH}.e2e_backup_{ts}"
        shutil.copy2(DB_PATH, backup)
        print(f"  DB 备份: {backup}")
        os.remove(DB_PATH)
        print(f"  DB 已删除")

    # 重启后端
    subprocess.run(["pkill", "-9", "-f", "uvicorn app.main:app"], capture_output=True)
    for _ in range(15):
        r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
        if ":8000" not in r.stdout:
            break
        time.sleep(1)

    subprocess.Popen(
        ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd="/workspace/embodied-ai-career-os/backend",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not wait_backend(60):
        print("  ✗ 后端重启超时")
        return False
    print("  ✓ DB 重置 + 后端重启完成")
    return True


# ================================================================
# 场景故事
# ================================================================

def run_scenario() -> E2ETest:
    test = E2ETest()

    # ===== 前置：基线 =====
    test.step("前置", "建立技能基线")
    if not wait_backend(10):
        test.fail("后端不可达")
        return test
    r = requests.get(f"{BACKEND_URL}/health", timeout=5)
    test.check("后端健康检查", r.status_code == 200, f"HTTP {r.status_code}")

    baseline = {
        "Isaac": get_skill("Isaac"),
        "ROS2": get_skill("ROS2"),
        "VLA": get_skill("VLA"),
    }
    test.check("3 个目标技能存在", all(baseline.values()),
               f"Isaac L={baseline['Isaac']['level']}, "
               f"ROS2 L={baseline['ROS2']['level']}, "
               f"VLA L={baseline['VLA']['level']}")
    test.ok()

    # ===== 步骤 1：查看技能缺口 =====
    test.step("步骤 1", "GET /api/skills 技能缺口分析")
    r = requests.get(f"{BACKEND_URL}/api/skills")
    body = r.json()
    test.check("GET /api/skills 成功", r.status_code == 200 and body["success"], f"HTTP {r.status_code}")
    skills = body["data"]
    test.check("10 项种子技能", len(skills) == 10, f"{len(skills)} 项")
    weak_skills = [s for s in skills if s["category"] == "Weak"]
    test.check("≥3 项弱技能", len(weak_skills) >= 3, f"{len(weak_skills)} 项")
    test.ok()

    # ===== 步骤 2：Planner 生成 3 个任务 =====
    test.step("步骤 2", "Planner 生成今日 3 个任务")
    task_specs = [
        {
            "name": "Isaac 任务",
            "skill_name": "Isaac",
            "payload": {
                "available_minutes": 60,
                "target_role": "Robot AI Engineer",
                "skills": [
                    {"name": "Isaac", "level": baseline["Isaac"]["level"], "target": 4},
                    {"name": "ROS2", "level": baseline["ROS2"]["level"], "target": 4},
                ],
                "current_focus": "Isaac",
                "energy_level": "high",
                "persist": True,
            },
        },
        {
            "name": "ROS2 任务",
            "skill_name": "ROS2",
            "payload": {
                "available_minutes": 40,
                "target_role": "Robot AI Engineer",
                "skills": [{"name": "ROS2", "level": baseline["ROS2"]["level"], "target": 4}],
                "energy_level": "normal",
                "persist": True,
            },
        },
        {
            "name": "VLA 任务",
            "skill_name": "VLA",
            "payload": {
                "available_minutes": 30,
                "target_role": "Robot AI Engineer",
                "skills": [{"name": "VLA", "level": baseline["VLA"]["level"], "target": 4}],
                "energy_level": "low",
                "persist": True,
            },
        },
    ]
    created_tasks: dict = {}
    before_tasks = db_count("tasks")
    before_planner_runs = db_count("agent_runs", "agent_name = 'planner'")

    for spec in task_specs:
        r = requests.post(f"{BACKEND_URL}/api/planner/generate", json=spec["payload"])
        body = r.json()
        ok = r.status_code == 200 and body["success"]
        test.check(f"{spec['name']} 生成", ok,
                   f"HTTP {r.status_code} skill={body.get('data', {}).get('skill', 'N/A')}")
        if ok:
            d = body["data"]
            created_tasks[spec["skill_name"]] = {
                "task_id": d["task_id"],
                "title": d["title"],
                "skill": d["skill"],
            }
            print(f"      → task#{d['task_id']}: {d['title']} (duration={d['duration']}min)")

    after_tasks = db_count("tasks")
    after_planner_runs = db_count("agent_runs", "agent_name = 'planner'")
    test.check("tasks 增加 3", after_tasks - before_tasks == 3,
               f"{before_tasks} → {after_tasks}")
    test.check("planner runs 增加 3", after_planner_runs - before_planner_runs == 3,
               f"{before_planner_runs} → {after_planner_runs}")
    test.ok()

    # ===== 步骤 3：提交 3 次复盘 =====
    review_payloads = {
        "Isaac": {  # Case A：充分证据
            "content": "成功在本地搭建 Isaac Sim 2023.1.1 环境并运行官方 Hello World Example。"
                       "总结：conda 环境 + nucleus 配置是关键。"
                       "反思：第一次启动加载耗时较长，需要提前下载素材。"
                       "改进：写自动化 install 脚本避免重复配置。",
            "duration_minutes": 55,
            "artifact_url": "https://github.com/myuser/isaac-sim-setup",
            "expect": {"score": 100, "level_up": True, "evidence_append": True},
        },
        "ROS2": {  # Case B：部分证据
            "content": "学习了 ROS2 Topic 通信，尝试写了一个简易 publisher 节点。"
                       "遇到 subscription QoS 兼容性问题，暂时未完全解决。",
            "duration_minutes": 35,
            "artifact_url": None,
            "expect": {"score_min": 50, "score_max": 79, "level_up": False, "evidence_append": True},
        },
        "VLA": {  # Case C：证据不足
            "content": "看了一会 VLA 介绍视频",
            "duration_minutes": 10,
            "artifact_url": None,
            "expect": {"score_max": 49, "level_up": False, "evidence_append": False},
        },
    }

    before_logs = db_count("learning_logs")
    before_assess = db_count("skill_assessments")
    before_reviewer_runs = db_count("agent_runs", "agent_name = 'reviewer'")

    for idx, (skill_name, info) in enumerate(created_tasks.items(), 1):
        test.step(f"步骤 3.{idx}", f"复盘 {skill_name}：{info['title'][:30]}")

        skill_before = get_skill(skill_name) or {}
        ev_before = len(skill_before.get("evidence") or [])

        rp = review_payloads[skill_name]
        r = requests.post(f"{BACKEND_URL}/api/reviewer/review", json={
            "task_id": info["task_id"],
            "content": rp["content"],
            "duration_minutes": rp["duration_minutes"],
            "artifact_url": rp["artifact_url"],
        })
        body = r.json()
        ok = r.status_code == 200 and body["success"]
        test.check("POST /api/reviewer/review", ok, f"HTTP {r.status_code}")
        if not ok:
            test.fail(f"Reviewer API 失败: {body}")
            continue

        result = body["data"]
        a = result["assessment"]
        updated = result["updated_skill"]
        score = a["evidence_score"]

        # 得分校验
        exp = rp["expect"]
        if "score" in exp:
            test.check(f"Score = {exp['score']}", score == exp["score"], f"实际 {score}")
        if "score_min" in exp:
            test.check(f"Score ≥ {exp['score_min']}", score >= exp["score_min"], f"实际 {score}")
        if "score_max" in exp:
            test.check(f"Score ≤ {exp['score_max']}", score <= exp["score_max"], f"实际 {score}")

        # 等级变化
        delta = a["new_level"] - a["old_level"]
        exp_delta = 1 if exp["level_up"] else 0
        test.check(
            f"等级 {a['old_level']}→{a['new_level']}（升级={exp['level_up']}）",
            delta == exp_delta, f"Δ{delta:+d}"
        )

        # evidence 追加
        ev_after = len(updated.get("evidence") or [])
        if exp["evidence_append"]:
            test.check(f"evidence 追加（{ev_before}→{ev_after}）", ev_after > ev_before)
        else:
            test.check(f"evidence 不变（{ev_before}→{ev_after}）", ev_after == ev_before)

        # Task → done
        task_row = db_query("SELECT status FROM tasks WHERE id = ?", (info["task_id"],))
        test.check("Task 状态 → done", task_row[0]["status"] == "done",
                   f"status={task_row[0]['status']}")

        print(f"      Score: {score} | 等级 {a['old_level']}→{a['new_level']} | "
              f"reason: {a['reason'][:60]}")
        test.ok()

    # ===== 步骤 4：数据一致性总验证 =====
    test.step("步骤 4", "全链路数据一致性总验证")
    after_logs = db_count("learning_logs")
    after_assess = db_count("skill_assessments")
    after_reviewer_runs = db_count("agent_runs", "agent_name = 'reviewer'")
    test.check("learning_logs +3", after_logs - before_logs == 3,
               f"{before_logs} → {after_logs}")
    test.check("skill_assessments +3", after_assess - before_assess == 3,
               f"{before_assess} → {after_assess}")
    test.check("reviewer runs +3", after_reviewer_runs - before_reviewer_runs == 3,
               f"{before_reviewer_runs} → {after_reviewer_runs}")

    assessments = db_query("SELECT * FROM skill_assessments ORDER BY id")
    reviewer_runs = db_query("SELECT * FROM agent_runs WHERE agent_name = 'reviewer' ORDER BY created_at")
    test.check("assessments ↔ reviewer_runs 数量匹配",
               len(assessments) == len(reviewer_runs),
               f"{len(assessments)} ↔ {len(reviewer_runs)}")

    # assessment.new_level == skill.level
    mismatches = 0
    for row in assessments:
        s = get_skill_by_id(row["skill_id"])
        if s and row["new_level"] != s["level"]:
            mismatches += 1
            test.check(
                f"Assessment#{row['id']} new_level == skill.level",
                row["new_level"] == s["level"],
                f"assessment.new={row['new_level']} vs skill={s['level']}"
            )
        elif s:
            test.check(
                f"Assessment#{row['id']} skill#{row['skill_id']} 等级一致",
                row["new_level"] == s["level"]
            )
    test.check(f"Assessment-Skill 一致性", mismatches == 0,
               f"不匹配 {mismatches}/{len(assessments)}")
    test.ok()

    # ===== 步骤 5：Dashboard 反射验证 =====
    test.step("步骤 5", "Dashboard 反射：GET /api/skills 等级变化")
    final_skills = {s["name"]: s for s in requests.get(f"{BACKEND_URL}/api/skills").json()["data"]}

    # Isaac 升级
    isaac_final = final_skills["Isaac"]
    test.check("Isaac 升级", isaac_final["level"] > baseline["Isaac"]["level"],
               f"{baseline['Isaac']['level']} → {isaac_final['level']}")
    test.check("Isaac evidence 增加",
               len(isaac_final["evidence"]) > len(baseline["Isaac"].get("evidence") or []),
               f"{len(baseline['Isaac'].get('evidence') or [])} → {len(isaac_final['evidence'])}")

    # ROS2 等级不变 evidence 增加
    ros2_final = final_skills["ROS2"]
    test.check("ROS2 等级不变", ros2_final["level"] == baseline["ROS2"]["level"],
               f"{baseline['ROS2']['level']} → {ros2_final['level']}")
    test.check("ROS2 evidence 增加",
               len(ros2_final["evidence"]) > len(baseline["ROS2"].get("evidence") or []),
               f"{len(baseline['ROS2'].get('evidence') or [])} → {len(ros2_final['evidence'])}")

    # VLA 全不变
    vla_final = final_skills["VLA"]
    test.check("VLA 等级不变", vla_final["level"] == baseline["VLA"]["level"],
               f"{baseline['VLA']['level']} → {vla_final['level']}")
    test.check("VLA evidence 不变",
               len(vla_final["evidence"]) == len(baseline["VLA"].get("evidence") or []),
               f"{len(baseline['VLA'].get('evidence') or [])} → {len(vla_final['evidence'])}")
    test.ok()

    # ===== 步骤 6：Planner 决策受影响验证 =====
    test.step("步骤 6", "Planner 反射：学习后 gap 减小，决策动态调整")
    skills_after = [
        {"name": "Isaac", "level": isaac_final["level"], "target": 4},
        {"name": "ROS2", "level": ros2_final["level"], "target": 4},
    ]
    r = requests.post(f"{BACKEND_URL}/api/planner/generate", json={
        "available_minutes": 45,
        "target_role": "Robot AI Engineer",
        "skills": skills_after,
        "persist": True,
    })
    data = r.json()["data"]
    selected = data["skill"]
    gap_isaac = 4 - isaac_final["level"]
    gap_ros2 = 4 - ros2_final["level"]
    test.check("学习后 Planner 重新选技能", selected in ("Isaac", "ROS2"),
               f"选择={selected} (Isaac gap={gap_isaac}, ROS2 gap={gap_ros2})")
    test.ok()

    return test


# ================================================================
# 报告生成
# ================================================================

def gen_report(test: E2ETest) -> bool:
    os.makedirs(REPORT_DIR, exist_ok=True)
    total = 0
    passed = 0
    steps_summary = []
    for step in test.steps:
        c = step["checks"]
        p = sum(1 for x in c if x["ok"])
        total += len(c)
        passed += p
        steps_summary.append({
            "section": step["section"],
            "description": step["description"],
            "status": step["status"],
            "total": len(c),
            "passed": p,
            "elapsed_ms": step.get("elapsed_ms", 0),
        })
    failed = total - passed
    rate = (passed / total * 100) if total else 0
    elapsed = int((time.perf_counter() - test.start_time) * 1000)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 控制台
    print("\n" + "="*70)
    print("  Day7 Learning Loop E2E 测试报告")
    print("="*70)
    print(f"  后端: {BACKEND_URL}")
    print(f"  DB: {DB_PATH}")
    print(f"  检查点: {total}  通过: {passed}  失败: {failed}  通过率: {rate:.1f}%")
    print(f"  总耗时: {elapsed}ms")
    print("-"*70)
    for s in steps_summary:
        sr = s['passed'] / s['total'] * 100 if s['total'] else 0
        icon = "✓" if s['status'] == "PASS" else "✗"
        print(f"  {icon} [{s['section']:<8}] {s['description'][:38]:<38}  {s['passed']}/{s['total']} ({sr:.0f}%)  {s['elapsed_ms']}ms")
    print("="*70)

    # JSON
    report = {
        "title": "Day7 Learning Loop E2E 测试报告",
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "checks": total, "passed": passed, "failed": failed,
            "pass_rate": round(rate, 2), "elapsed_ms": elapsed,
            "overall": "PASS" if failed == 0 else "FAIL",
        },
        "steps": test.steps,
    }
    jp = os.path.join(REPORT_DIR, f"day7_e2e_{ts}.json")
    with open(jp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"  JSON → {jp}")

    # Markdown
    md = os.path.join(REPORT_DIR, f"day7_e2e_{ts}.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("# Day7 Learning Loop E2E 测试报告\n\n")
        f.write(f"- 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- 后端: `{BACKEND_URL}` / DB: `{DB_PATH}`\n")
        f.write(f"- **通过率: {rate:.1f}%** ({passed}/{total})\n")
        f.write(f"- 总耗时: {elapsed}ms\n\n")
        f.write("## 场景故事\n\n")
        f.write("模拟 Robot AI Engineer 转型候选人的完整学习日：\n\n")
        f.write("1. 建立技能基线\n")
        f.write("2. GET /api/skills 查看缺口 → 3 项弱技能\n")
        f.write("3. Planner 生成 Isaac/ROS2/VLA 3 个任务 → tasks +3, planner agent_runs +3\n")
        f.write("4. 提交复盘（3 种证据质量）→ Isaac 升级 + ROS2 加 evidence + VLA 不变\n")
        f.write("5. 数据一致性：logs/assess/reviewer_runs 各自 +3\n")
        f.write("6. Dashboard 反射：GET /api/skills 可见等级/evidence 更新\n")
        f.write("7. Planner 反射：gap 变化影响下次决策\n\n")
        f.write("## 步骤汇总\n\n")
        f.write("| 步骤 | 描述 | 检查点 | 耗时 |\n|------|------|--------|------|\n")
        for s in steps_summary:
            f.write(f"| {s['section']} | {s['description']} | {s['passed']}/{s['total']} | {s['elapsed_ms']}ms |\n")
    print(f"  MD   → {md}")

    return failed == 0


def main():
    print("="*70)
    print("  Day7 Learning Loop E2E 测试启动")
    print("="*70)

    if not reset_backend_and_db():
        sys.exit(1)

    test = run_scenario()
    ok = gen_report(test)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
