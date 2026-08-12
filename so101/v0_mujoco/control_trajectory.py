"""SO101 V0 关节轨迹插值控制 Demo。

与 control_demo.py 的区别:
    - control_demo.py:  一次性把 ctrl 设到终点 → 跳变 + 振荡
    - control_trajectory.py: 在相邻 waypoint 之间做【线性插值】,
                              每 50 步更新一次 ctrl → 平滑运动

用法:
    python control_trajectory.py              # 无头运行
    python control_trajectory.py --view       # 3D 可视化（推荐）
    python control_trajectory.py --record     # 录制轨迹 + CSV + 绘图
    python control_trajectory.py --view --record  # 可视化 + 录制

核心思路（三层循环）:
    外层: 遍历相邻 waypoint 对 (A → B),每对算一段
    中层: 在本段内按 num_updates 次爬台阶 (每次更新 ctrl 一次)
    内层: 每次更新后跑 50 步 mujoco.mj_step,让 PD 控制器跟随当前目标
"""
from __future__ import annotations

import csv
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

# ---------- 插值参数 ----------
UPDATE_EVERY = 50                # 每 50 步更新一次 ctrl（README 要求）
DURATION_PER_SEGMENT = 500       # 每段（相邻 waypoint 之间）走的总步数

# ---------- 角度单位转换 ----------
# Mujoco 的 data.ctrl 接收【弧度 rad】,但人习惯用【度 °】写 waypoint。
# 统一策略: waypoint 用度存储,进入插值前一次性转成弧度,
# 之后所有计算都在弧度空间进行,写 ctrl 时不再做任何转换。
DEG2RAD = np.pi / 180.0   # 1 度 = π/180 弧度 ≈ 0.0174533 rad


def waypoints_deg_to_rad(waypoints_deg):
    """把 waypoint 列表从【度】转成【弧度】。

    输入: [("Home", [0, 90, -45]), ...]
    输出: [("Home", array([0.0, 1.5708, -0.7854])), ...]
    """
    waypoints_rad = []
    for label, angles_deg in waypoints_deg:
        angles_deg = np.asarray(angles_deg, dtype=float)   # 转 numpy 数组
        angles_rad = angles_deg * DEG2RAD                    # 度 → 弧度（核心一行）
        waypoints_rad.append((label, angles_rad))
    return waypoints_rad


# ---------- JSON 配置加载 ----------
def load_poses() -> tuple[int, list[tuple[str, list[float]]]]:
    """读取 poses.json,返回 (step_count, [(label, angles), ...])。"""
    with open(POSES_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    step_count = config.get("step_count", 3000)
    poses = [(p["label"], p["angles"]) for p in config["poses"]]
    return step_count, poses


# ---------- 核心: waypoint 线性插值 ----------
def interpolate_waypoints(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    waypoints: list[tuple[str, np.ndarray]],
    duration_per_segment: int = DURATION_PER_SEGMENT,
    update_every: int = UPDATE_EVERY,
    viewer=None,
    records: list[dict] | None = None,
) -> None:
    """在相邻 waypoint 之间做线性插值,平滑运动通过所有航点。

    Args:
        waypoints: [(label, angles_rad), ...]  已经转成弧度的航点列表
        duration_per_segment: 每段（A→B）走的总步数
        update_every: 每 N 步更新一次 ctrl
        viewer: 可视化句柄（可选）
        records: 轨迹录制列表（可选,传入后会自动记录）

    三层循环:
        外层 k: 遍历相邻 waypoint 对 (A, B)
        中层 i: 在本段内按 num_updates 次爬台阶
        内层:   每次更新后跑 update_every 步 mj_step
    """
    n_joints = model.njnt
    # 每段需要更新 ctrl 的次数（比如 500 步 / 50 步 = 10 次）
    num_updates = duration_per_segment // update_every

    # 外层:遍历相邻 waypoint 对 (A → B)
    for k in range(len(waypoints) - 1):
        label_a, A_rad = waypoints[k]
        label_B, B_rad = waypoints[k + 1]

        # 防御:关节维度对不上时截断/补零
        if len(A_rad) != n_joints or len(B_rad) != n_joints:
            print(f"  WARNING: {label_a}→{label_B} 关节数与模型不符,已截断/补零")
            A_rad = np.asarray(A_rad[:n_joints] + [0.0] * max(0, n_joints - len(A_rad)))
            B_rad = np.asarray(B_rad[:n_joints] + [0.0] * max(0, n_joints - len(B_rad)))

        print(f"\n>>> 段 {k + 1}: {label_a}  →  {label_B}")
        print(f"    起点: {[f'{np.degrees(a):6.1f}°' for a in A_rad]}")
        print(f"    终点: {[f'{np.degrees(b):6.1f}°' for b in B_rad]}")
        print(f"    参数: {duration_per_segment} 步 / 每 {update_every} 步更新 = {num_updates} 次台阶")

        # 中层:在本段内按 num_updates 次爬台阶
        # range(num_updates + 1) 是为了取到 i = num_updates,即 t = 1.0,确保到达终点 B
        for i in range(num_updates + 1):
            t = i / num_updates   # 进度: 0.0, 0.1, 0.2, ..., 1.0

            # ====== 线性插值核心一行 ======
            # 对每个关节独立做: target = A + (B - A) * t
            # numpy 会按位运算,所以一行搞定所有关节
            current_target_rad = A_rad + (B_rad - A_rad) * t

            # 把当前插值目标写进 ctrl
            for j in range(n_joints):
                data.ctrl[j] = current_target_rad[j]

            # 内层:跑 update_every 步,让 PD 控制器跟随当前 ctrl
            for step in range(update_every):
                mujoco.mj_step(model, data)
                # 每 10 步录一次轨迹（200Hz → 20Hz 采样）
                if records is not None and step % 10 == 0:
                    records.append({
                        "t": round(data.time, 4),
                        **{f"joint_{j}_deg": round(np.degrees(data.qpos[j]), 3)
                           for j in range(n_joints)},
                    })
                # 可视化刷新（每 10 步刷一次,避免太频繁）
                if viewer and viewer.is_running() and step % 10 == 0:
                    viewer.sync()
                if viewer and not viewer.is_running():
                    return

            # 打印本次台阶的进度（便于调试）
            if i % max(1, num_updates // 5) == 0:   # 每段最多打印 5~6 次
                actual = [f"{np.degrees(data.qpos[j]):6.2f}°" for j in range(n_joints)]
                print(f"    t={t:.2f}  target={[f'{np.degrees(x):5.1f}°' for x in current_target_rad]}  actual={actual}")

        # 本段结束,打印最终实际角度
        actual = [f"{np.degrees(data.qpos[j]):6.2f}°" for j in range(n_joints)]
        print(f"    [段结束] 实际: {actual}")

        if viewer and not viewer.is_running():
            return


# ---------- 轨迹保存与绘图 ----------
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
    if not records:
        return
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

    joint_names = ["Base Rotation", "Shoulder Pitch", "Elbow Pitch", "Wrist Roll"]
    colors = ["#4C72B0", "#55A868", "#C44E52", "#8172B3"]

    for i, ax in enumerate(axes):
        joint_key = f"joint_{i}_deg"
        angles = [r[joint_key] for r in records]
        ax.plot(times, angles, linewidth=2, color=colors[i % len(colors)])
        ax.set_ylabel(f"{joint_names[i]} (°)")
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Time (s)")
    fig.suptitle("SO101 Mujoco Joint Trajectory (Waypoint Interpolation)", fontsize=12, fontweight="bold")
    fig.tight_layout()

    if filepath:
        fig.savefig(filepath, dpi=120)
        print(f"图表已保存: {filepath}")
    else:
        plt.show()


# ---------- 主入口 ----------
def main() -> None:
    use_viewer = "--view" in sys.argv
    use_record = "--record" in sys.argv

    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    print("=" * 60)
    print("SO101 V0: Mujoco 关节轨迹插值控制")
    print(f"pose 文件: {POSES_PATH}")
    print(f"插值参数: 每段 {DURATION_PER_SEGMENT} 步,每 {UPDATE_EVERY} 步更新一次 ctrl")
    if use_viewer:
        print("模式: 3D 可视化")
    if use_record:
        print("模式: 轨迹录制")
    print("=" * 60)

    # 加载初始配置
    _, poses_deg = load_poses()
    last_mtime = os.path.getmtime(POSES_PATH)

    # ---- 可视化模式 ----
    if use_viewer:
        with mujoco.viewer.launch_passive(model, data) as viewer:
            # 首次播放:度 → 弧度 → 插值
            waypoints_rad = waypoints_deg_to_rad(poses_deg)
            records: list[dict] = []
            interpolate_waypoints(
                model, data, waypoints_rad,
                viewer=viewer,
                records=records if use_record else None,
            )
            if not viewer.is_running():
                if use_record and records:
                    out_dir = Path(__file__).parent / "output"
                    save_trajectory(records, str(out_dir / "trajectory.csv"))
                    plot_trajectory(records, str(out_dir / "trajectory.png"))
                return

            # 录制模式:播放完后保存并退出
            if use_record and records:
                out_dir = Path(__file__).parent / "output"
                save_trajectory(records, str(out_dir / "trajectory.csv"))
                plot_trajectory(records, str(out_dir / "trajectory.png"))
                print("\n[OK] 录制完成")
                return

            print("\n" + "=" * 60)
            print("等待变更... (编辑 poses.json 并保存,或关闭窗口退出)")
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
                        _, poses_deg = load_poses()
                    except Exception as e:
                        print(f"  ERROR: JSON 解析失败: {e}")
                        continue

                    # 重置仿真状态,按新配置重放
                    mujoco.mj_resetData(model, data)
                    waypoints_rad = waypoints_deg_to_rad(poses_deg)
                    interpolate_waypoints(model, data, waypoints_rad, viewer=viewer)

        print("\n[OK] Demo 退出")

    # ---- 无头模式 ----
    else:
        waypoints_rad = waypoints_deg_to_rad(poses_deg)
        records: list[dict] = []
        interpolate_waypoints(
            model, data, waypoints_rad,
            records=records if use_record else None,
        )
        if use_record and records:
            out_dir = Path(__file__).parent / "output"
            save_trajectory(records, str(out_dir / "trajectory.csv"))
            plot_trajectory(records, str(out_dir / "trajectory.png"))
        print("\n[OK] Demo 完成")


if __name__ == "__main__":
    main()
