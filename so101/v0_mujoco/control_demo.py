"""SO101 V0 关节控制 Demo + 热重载。

每当你修改 poses.json，机械臂自动按新参数重放，不用关窗口、不用重启脚本。

用法:
    python control_demo.py          # 无头运行
    python control_demo.py --view   # 3D 可视化 + 热重载（推荐）

热重载工作流:
    1. 跑 python control_demo.py --view
    2. 在 VSCode 里编辑 poses.json，Ctrl+S 保存
    3. 机械臂自动重放新姿态
    4. 反复改、反复看，直到满意
    5. 关 3D 窗口退出
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import mujoco
import mujoco.viewer  # noqa: F401 — 可视化
import numpy as np

MODEL_PATH = Path(__file__).parent / "so101_arm.xml"
POSES_PATH = Path(__file__).parent / "poses.json"


# ---------- JSON 配置加载 ----------
def load_poses() -> tuple[int, list[tuple[str, list[float]]]]:
    """读取 poses.json，返回 (step_count, [(label, angles), ...])。"""
    with open(POSES_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    step_count = config.get("step_count", 3000)
    poses = [(p["label"], p["angles"]) for p in config["poses"]]
    return step_count, poses


# ---------- 仿真 ----------
def play_poses(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    step_count: int,
    poses: list[tuple[str, list[float]]],
    viewer=None,
) -> None:
    """按顺序播放各组目标姿态。"""
    for label, angles_deg in poses:
        n_joints = model.njnt
        if len(angles_deg) != n_joints:
            print(f"  WARNING: {label} 需要 {n_joints} 个角度，但给出了 {len(angles_deg)} 个，已截断/补零")
            angles_deg = angles_deg[:n_joints] + [0.0] * max(0, n_joints - len(angles_deg))

        target_rad = np.radians(angles_deg)
        print(f"\n>>> {label}")
        print(f"    目标: {[f'{a:6.1f}°' for a in angles_deg]}")

        for i, tgt in enumerate(target_rad):
            data.ctrl[i] = tgt

        for step in range(step_count):
            mujoco.mj_step(model, data)
            if viewer and viewer.is_running() and step % 10 == 0:
                viewer.sync()
            if viewer and not viewer.is_running():
                return

        # 打印实际角度
        actual = [f"{np.degrees(data.qpos[i]):6.2f}°" for i in range(n_joints)]
        print(f"    实际: {actual}")

        if viewer and not viewer.is_running():
            return


# ---------- 主入口 ----------
def main() -> None:
    use_viewer = "--view" in sys.argv

    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    print("=" * 60)
    print("SO101 V0: Mujoco 关节控制 Demo")
    print(f"pose 文件: {POSES_PATH}")
    if use_viewer:
        print("模式: 3D 可视化 + 热重载（编辑 poses.json 即自动重放）")
    print("=" * 60)

    # 加载初始配置
    step_count, poses = load_poses()
    last_mtime = os.path.getmtime(POSES_PATH)

    # ---- 可视化模式 ----
    if use_viewer:
        with mujoco.viewer.launch_passive(model, data) as viewer:
            # 首次播放
            play_poses(model, data, step_count, poses, viewer=viewer)
            if not viewer.is_running():
                return

            print("\n" + "=" * 60)
            print("等待变更... (编辑 poses.json 并保存，或关闭窗口退出)")
            print("=" * 60)

            # 热重载循环
            while viewer.is_running():
                time.sleep(0.5)  # 0.5 秒轮询

                # 检查 poses.json 是否被修改
                try:
                    new_mtime = os.path.getmtime(POSES_PATH)
                except OSError:
                    continue

                if new_mtime > last_mtime:
                    last_mtime = new_mtime
                    print("\n>>> poses.json changed, reloading...")
                    try:
                        step_count, poses = load_poses()
                    except Exception as e:
                        print(f"  ERROR: JSON 解析失败: {e}")
                        continue

                    # 重置仿真状态，按新配置重放
                    mujoco.mj_resetData(model, data)
                    play_poses(model, data, step_count, poses, viewer=viewer)

        print("\n[OK] Demo 退出")

    # ---- 无头模式 ----
    else:
        play_poses(model, data, step_count, poses)
        print("\n[OK] Demo 完成")


if __name__ == "__main__":
    main()
