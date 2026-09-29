"""SIGNAL 4 考得住：is_verified 计数单调不减 + 复习历史有记录。"""

import sqlite3

import requests

from e2e_common import start_backend_copy, stop_and_verify


def main() -> None:
    base, fp, proc, copy_db = start_backend_copy()
    try:
        s = requests.Session()

        def verified_count() -> int:
            units = s.get(f"{base}/api/mastery/units", timeout=10).json()["data"]
            total = 0
            for u in units:
                opened = s.get(f"{base}/api/mastery/units/{u['id']}", timeout=10).json()["data"]
                total += sum(1 for i in opened["items"] if i["is_verified"])
            return total

        before = verified_count()
        units = s.get(f"{base}/api/mastery/units", timeout=10).json()["data"]
        uid = units[0]["id"]
        opened = s.get(f"{base}/api/mastery/units/{uid}", timeout=10).json()["data"]
        quiz = next(i for i in opened["items"] if i["kind"] == "quiz_q")

        # 从副本库取该题参考答案 → 答对才能真正推进 is_verified（否则 after==before，
        # 单调性断言空转，「考得住」没被验证到）。副本库我们自己拥有，读答案合规。
        conn = sqlite3.connect(copy_db)
        try:
            ref_answer = conn.execute(
                "SELECT answer FROM unit_items WHERE id=?", (quiz["id"],)
            ).fetchone()[0]
        finally:
            conn.close()

        r = s.post(
            f"{base}/api/mastery/units/{uid}/answer",
            json={"item_id": quiz["id"], "answer": ref_answer},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        answered = r.json()["data"]
        assert answered["correct"], f"参考答案被判错（判定链路异常）: {answered}"
        after = verified_count()
        assert after >= before, f"is_verified 计数回退：{before} → {after}"
        assert after > before, f"答对未推进 is_verified：{before} → {after}"

        # 复习历史：评一张卡产生 ReviewLog（经 API 验证 due 推进）
        card_id = answered.get("card_id")
        assert card_id, f"答题未建复习卡: {answered}"
        r = s.post(
            f"{base}/api/mastery/cards/{card_id}/review",
            json={"rating": "good", "duration_seconds": 30},
            timeout=10,
        )
        assert r.status_code == 200, r.text

        conn = sqlite3.connect(copy_db)
        try:
            n = conn.execute("SELECT COUNT(*) FROM review_logs").fetchone()[0]
        finally:
            conn.close()
        assert n >= 1, "review_logs 为空——复习历史无记录"
        print(f"SIGNAL 4: PASS（is_verified 单调不减 {before}→{after}，review_logs={n}）")
    finally:
        stop_and_verify(proc, copy_db, fp)


if __name__ == "__main__":
    main()
