"""SIGNAL 3 作品集说话：SFT/LoRA-QLoRA/DPO 有 L2+ 证据 → 13 节 README 组装。"""

from pathlib import Path

import requests

from e2e_common import start_backend_copy, stop_and_verify

# 造 L2+ 证据：直接走 apply 层事件（E2E 验证组装链路，证据真实性由日常流保证）
# 技能名以 skills 表为准（app/core/skill_profile.py）：是 "LoRA/QLoRA"，不是 "LoRA"。
SKILLS = ["SFT", "LoRA/QLoRA", "DPO"]


def main() -> None:
    base, fp, proc, copy_db = start_backend_copy()
    try:
        # ⚠️ DATABASE_URL 必须先指向副本，再 import app.*（顺序同 conftest 的隔离逻辑：
        # app.db.base 在 import 时读 settings.database_url 建 engine）。
        import os
        import sys

        os.environ["DATABASE_URL"] = f"sqlite:///{copy_db.as_posix()}"
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from app.db.base import SessionLocal
        from app.services.evidence_events import record_evidence_event

        db = SessionLocal()
        try:
            for sk in SKILLS:
                result = record_evidence_event(db, sk, "commit", f"commit:e2e-{sk}")
                # 幂等：副本库若已带 gate≥2（上次跑过），record_evidence_event 返回
                # applied=False 的 no-op —— 端态仍达标，不能假失败。
                assert result["applied"] or result["from_gate"] >= 2, f"事件未落库且门未达标: {result}"
        finally:
            db.close()

        out = requests.get(f"{base}/api/portfolio/assemble", timeout=10).json()["data"]
        assert len(out["sections"]) == 13, f"节数 {len(out['sections'])} != 13"
        for sec in out["sections"]:
            assert sec["content"].strip(), f"节「{sec['name']}」为空"
        for sk in SKILLS:
            assert sk in out["ready_skills"], f"{sk} 未就绪: {out['ready_skills']}"

        # L2+ 复核：副本库里三技能 evidence_gate 应被 commit 事件抬到 ≥2
        import sqlite3

        conn = sqlite3.connect(copy_db)
        try:
            gates = dict(conn.execute(
                "SELECT name, evidence_gate FROM skills WHERE name IN (?,?,?)",
                SKILLS,
            ).fetchall())
        finally:
            conn.close()
        for sk in SKILLS:
            assert gates.get(sk, 0) >= 2, f"{sk} gate 未到 L2: {gates}"

        print("SIGNAL 3: PASS（三模块 L2+，13 节 README 非空）")
    finally:
        stop_and_verify(proc, copy_db, fp)


if __name__ == "__main__":
    main()
