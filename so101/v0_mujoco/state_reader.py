"""关节状态读取器。

模式:
    record     — 设置目标关节角度，录制运动轨迹 → CSV + 绘图  (默认)
    continuous — 持续打印实时 joint states

用法:
    python state_reader.py record       # 录制轨迹
    python state_reader.py continuous   # 持续监测
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import mujoco
import numpy as np

MODEL_PATH = Path(__file__).parent / "so101_arm.xml"


def continuous_monitor(duration_s: float = 5.0) -> None:
    """实时打印关节状态，持续 duration_s 秒。"""
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    steps = int(duration_s / model.opt.timestep)
    print(f"持续监测 {duration_s}s (timestep={model.opt.timestep:.4f}s, {steps} steps)")

    for step in range(steps):
        mujoco.mj_step(model, data)
        if step % 50 == 0:
            t = step * model.opt.timestep
            angles = [f"{np.degrees(data.qpos[i]):6.1f}°" for i in range(model.njnt)]
            print(f"  t={t:.2f}s | " + " | ".join(angles))


def record_trajectory(
    target_joints: list[float], duration_s: float = 3.0
) -> list[dict]:
    """设置目标关节角度，录制运动轨迹，返回时间序列数据。

    Args:
        target_joints: 目标关节角度 (度) [base, shoulder, elbow]
        duration_s: 仿真时长 (秒)

    Returns:
        [{t, joint_0_deg, joint_1_deg, joint_2_deg}, ...]
    """
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    target_rad = np.radians(target_joints)
    for i, tgt in enumerate(target_rad):
        data.ctrl[i] = tgt

    records: list[dict] = []
    steps = int(duration_s / model.opt.timestep)

    for step in range(steps):
        mujoco.mj_step(model, data)
        if step % 10 == 0:  # 每 10 步记录一次（200Hz → 20Hz）
            records.append({
                "t": round(step * model.opt.timestep, 4),
                **{f"joint_{i}_deg": round(np.degrees(data.qpos[i]), 3)
                   for i in range(model.njnt)},
            })

    return records


def save_trajectory(records: list[dict], filepath: str) -> None:
    """导出轨迹到 CSV。"""
    if not records:
        return
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    print(f"轨迹已保存: {filepath} ({len(records)} 行)")


def plot_trajectory(records: list[dict], filepath: str | None = None) -> None:
    """绘制关节角度随时间变化曲线。"""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("需要 matplotlib: pip install matplotlib")
        return

    times = [r["t"] for r in records]
    n_joints = len([k for k in records[0] if k.startswith("joint_")])

    fig, axes = plt.subplots(n_joints, 1, figsize=(8, 2 * n_joints), sharex=True)
    if n_joints == 1:
        axes = [axes]

    joint_names = ["Base Rotation", "Shoulder Pitch", "Elbow Pitch"]

    for i, ax in enumerate(axes):
        joint_key = f"joint_{i}_deg"
        angles = [r[joint_key] for r in records]
        ax.plot(times, angles, linewidth=2, color=["#4C72B0", "#55A868", "#C44E52"][i])
        ax.set_ylabel(f"{joint_names[i]} (°)")
        ax.grid(True, alpha=0.3)
        ax.axhline(y=angles[-1], color="gray", linestyle="--", alpha=0.5, linewidth=0.8)

    axes[-1].set_xlabel("Time (s)")
    fig.suptitle("SO101 Mujoco Joint Trajectory", fontsize=12, fontweight="bold")
    fig.tight_layout()

    if filepath:
        fig.savefig(filepath, dpi=120)
        print(f"图表已保存: {filepath}")
    else:
        plt.show()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "record"

    if mode == "continuous":
        continuous_monitor(3.0)
    elif mode == "record":
        print("录制轨迹: base=30°, shoulder=-45°, elbow=60°")
        records = record_trajectory([30.0, -45.0, 60.0], duration_s=3.0)
        out_dir = Path(__file__).parent / "output"
        csv_path = out_dir / "trajectory.csv"
        png_path = out_dir / "trajectory.png"
        save_trajectory(records, str(csv_path))
        plot_trajectory(records, str(png_path))
    else:
        print(f"未知模式: {mode}. 可选: continuous | record")
