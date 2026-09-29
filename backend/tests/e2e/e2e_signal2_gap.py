"""SIGNAL 2 差距可量化：雷达/证据接口可答「补了哪块」，主张带 evidence 引用。"""

import requests

from e2e_common import start_backend_copy, stop_and_verify


def main() -> None:
    base, fp, proc, copy_db = start_backend_copy()
    try:
        s = requests.Session()
        evidence = s.get(f"{base}/api/skills/evidence", timeout=10).json()["data"]
        assert evidence, "证据清单为空"
        # 每条主张（gate≥1）必须带引用。
        # 实际响应形状（app/api/skills.py list_evidence）：
        #   {id, name, level, target_level, evidence_gate, evidence:[{level,kind,label,ref}]}
        # ——引用在 evidence[].ref 里（brief 草稿里的 refs/evidence_refs 是提案通道字段，
        # 不在本端点响应上），故按真实形状断言。
        claimed = 0
        for row in evidence:
            gate = row.get("gate", row.get("evidence_gate", 0))
            if gate >= 1:
                claimed += 1
                items = row.get("evidence") or []
                assert items, f"{row.get('name')} gate≥1 但 evidence 清单为空"
                for ev in items:
                    assert ev.get("ref"), f"{row.get('name')} 证据条目缺 ref 引用: {ev}"
        assert claimed, "没有任何 gate≥1 的技能——证据推导链路失效"
        # 今日聚合可回答「本周补了哪块」的原料：review + logs 齐备
        today = s.get(f"{base}/api/today", timeout=10).json()["data"]
        assert "review" in today and "learning_logs_24h" in today
        print(
            f"SIGNAL 2: PASS（{claimed} 条 gate≥1 主张全部带 evidence ref 引用，"
            "今日聚合含 review + learning_logs_24h）"
        )
    finally:
        stop_and_verify(proc, copy_db, fp)


if __name__ == "__main__":
    main()
