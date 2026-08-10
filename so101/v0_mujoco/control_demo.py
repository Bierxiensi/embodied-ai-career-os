"""SO101 V0 关节控制 Demo。

目标：用 Python 设置 joint positions → Mujoco 仿真 → 读取实际 joint states。

运行：
    python control_demo.py
"""
from __future__ import annotations

import time
from pathlib import Path

import mujoco
import numpy as np

MODEL_PATH = Path(__file__).parent / "so101_arm.xml"


def print_joint_states(data: mujoco.MjData, model: mujoco.MjModel) -> None:
    """打印当前关节角度（度）。"""
    for i in range(model.njnt):
        name = model.joint(i).name
        pos_deg = np.degrees(data.qpos[i])
        print(f"  {name}: {pos_deg:7.2f}°")


def main() -> None:
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    # 四组目标姿态 (base_rotation, shoulder_pitch, elbow_pitch) 单位：度
    poses = [
        ("Home",       [0.0,   0.0,   0.0]),
        ("Reach out",  [30.0, -30.0, 60.0]),
        ("Reach up",   [0.0,  -60.0, 90.0]),
        ("Retract",    [0.0,   20.0, 30.0]),
    ]

    print("=" * 50)
    print("SO101 V0: Mujoco 关节控制 Demo")
    print("=" * 50)

    with mujoco.Renderer(model, 480, 640) as renderer:
        for label, targets_deg in poses:
            print(f"\n>>> 目标姿态: {label}")
            print(f"    目标角度: {[f'{t:6.1f}°' for t in targets_deg]}")

            target_rad = np.radians(targets_deg)

            # 设置 actuator 目标位置
            for i, tgt in enumerate(target_rad):
                data.ctrl[i] = tgt

            # 仿真 3000 步（约 6 秒），让 arm 平稳到达目标
            for _ in range(3000):
                mujoco.mj_step(model, data)

            # 读取并打印当前关节状态
            print("  实际关节角度:")
            print_joint_states(data, model)

            # 渲染一帧
            renderer.update_scene(data)
            renderer.render()

            time.sleep(0.5)

    print("\n✅ Demo 完成")
    print("提示：安装被动 viewer 可实时观看 → pip install mujoco-python-viewer")


if __name__ == "__main__":
    main()
