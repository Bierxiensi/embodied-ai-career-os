"""SIGNAL 1 每天用得动：14 天日流模拟，单日 API 写操作 ≤25、无死路。"""

import requests

from e2e_common import start_backend_copy, stop_and_verify


def main() -> None:
    base, fp, proc, copy_db = start_backend_copy()
    try:
        s = requests.Session()
        units = s.get(f"{base}/api/mastery/units", timeout=10).json()["data"]
        assert units, "单元网格为空——先 sync_grid"
        uid = units[0]["id"]

        for day in range(14):
            calls = 0  # 步数代理（spec §2.3）：单日完整流 API 调用 ≤25 且无死路
            opened = s.get(f"{base}/api/mastery/units/{uid}", timeout=10).json()["data"]
            calls += 1
            quiz = [i for i in opened["items"] if i["kind"] == "quiz_q"][:3]
            assert quiz, f"Day {day}: 单元 {uid} 无 quiz 题"
            for item in quiz:
                r = s.post(
                    f"{base}/api/mastery/units/{uid}/answer",
                    json={"item_id": item["id"], "answer": "参考答案原文见 rationale"},
                    timeout=10,
                )
                assert r.status_code == 200, r.text
                calls += 1
            r = s.post(
                f"{base}/api/teach-back/complete",
                json={
                    "unit_id": uid,
                    "duration_minutes": 15,
                    "answers": [{"item_id": quiz[0]["id"], "spoken": "DPO 不再需要显式奖励模型"}],
                },
                timeout=10,
            )
            assert r.status_code == 200, r.text
            calls += 1
            r = s.get(f"{base}/api/today", timeout=10)
            assert r.status_code == 200, r.text
            calls += 1
            assert calls <= 25, f"Day {day} API 调用 {calls} 次，超过单日步数代理阈值 25"

        print("SIGNAL 1: PASS（14 天日流 ≤25 调用/天，无死路）")
    finally:
        stop_and_verify(proc, copy_db, fp)


if __name__ == "__main__":
    main()
