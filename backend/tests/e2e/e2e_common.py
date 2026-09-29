"""E2E 公共件：副本库起后端 + 指纹比对（绝不写开发库，沿用项目 §4.5 手法）。"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
DEV_DB = BACKEND / "data" / "app.db"

# Windows 控制台默认 cp936，打不出 ✅/中文 → 统一重配为 UTF-8（须在任何 print 之前，
# 本模块是四支脚本的首个项目内 import，满足该时序）。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def db_fingerprint(db_path: Path) -> str:
    h = hashlib.sha256()
    h.update(db_path.read_bytes() if db_path.exists() else b"missing")
    return h.hexdigest()[:16]


def start_backend_copy(port: int = 8011):
    """复制开发库 → 副本，起独立端口后端。返回 (base_url, fingerprint_before, proc, copy_db)。"""
    copy_db = BACKEND / "data" / f"e2e-copy-{port}.db"
    shutil.copy2(DEV_DB, copy_db)
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{copy_db.as_posix()}",
        "LLM_PROVIDER": os.environ.get("LLM_PROVIDER", "mock"),
        # Windows/venv：uvicorn 控制台输出走 GBK 会崩，钉死 UTF-8
        "PYTHONIOENCODING": "utf-8",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
        cwd=BACKEND,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    # 首次拉起（建表 + import langgraph 等）可达 30-60s → 90s 上限
    for _ in range(180):
        time.sleep(0.5)
        try:
            import requests

            if requests.get(f"{base}/health", timeout=1).status_code == 200:
                break
        except Exception:
            continue
    else:
        proc.kill()
        copy_db.unlink(missing_ok=True)
        raise RuntimeError("backend copy failed to start")
    return base, db_fingerprint(DEV_DB), proc, copy_db


def stop_and_verify(proc, copy_db: Path, fingerprint_before: str) -> None:
    proc.terminate()
    proc.wait(timeout=10)
    after = db_fingerprint(DEV_DB)
    assert after == fingerprint_before, f"开发库被改动！before={fingerprint_before} after={after}"
    # Windows：本进程若曾 import app.*（如 signal3 的 SessionLocal），engine 连接池
    # 会占着副本库句柄 → 先释放再删；再带重试兜底后端句柄释放的时延。
    # 只在 app 已被 import 时 dispose —— 否则会以默认 DATABASE_URL 新建 engine。
    if "app.db.base" in sys.modules:
        sys.modules["app.db.base"].engine.dispose()
    for attempt in range(10):
        try:
            copy_db.unlink(missing_ok=True)
            break
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.5)
    print("开发库指纹一致 ✅")
