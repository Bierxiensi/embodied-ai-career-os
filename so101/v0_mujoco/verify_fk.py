"""FK 验证脚本: 用三角函数手算末端位置,与 Mujoco 对比。

正向运动学(Forward Kinematics, FK):
    给定关节角度 → 末端执行器在空间中的位置 (x, y, z)

模型几何参数(从 so101_arm.xml 读取):
    BASE_Z = 0.4m    肩部高度 (base pos=0.3 + upper_arm pos=0.1)
    L1 = 0.3m        上臂长度 (upper_arm geom fromto 终点 z=0.3)
    L2 = 0.24m       前臂长度 (forearm geom fromto 终点 z=0.24)
    L3 = 0.24m       末端 site 偏移 (end_effector site pos z=0.24)

关节说明:
    θ0 = base_rotation   绕 Z 轴 (左右转头)
    θ1 = shoulder_pitch  绕 Y 轴 (前后摆臂)
    θ2 = elbow_pitch     绕 Y 轴 (前后弯肘) — 假设与 shoulder 同平面
    wrist 设为 0,site 沿前臂方向延伸 L3

核心公式(角度从 Z 轴量起,θ=0 时连杆竖直):
    竖直分量 z 用 cos,水平分量 x 用 sin
    elbow 总角度 = θ1 + θ2 (相对角度累加)
"""
import mujoco
import numpy as np

# ---------- 几何参数(从 so101_arm.xml 读出) ----------
BASE_Z = 0.4    # 肩部高度: 0.3(base pos) + 0.1(upper_arm pos)
L1 = 0.3        # 上臂长: upper_arm geom fromto="0 0 0  0 0 0.3"
L2 = 0.24       # 前臂长: forearm geom fromto="0 0 0  0 0 0.24"
L3 = 0.24       # 末端 site 偏移: end_effector site pos="0 0 0.24"


def compute_fk(joint_angles_deg):
    """用三角函数手算末端执行器位置。

    Args:
        joint_angles_deg: [θ0, θ1, θ2, ...] 角度(度),至少前 3 个

    Returns:
        (x, y, z): 末端在世界坐标系下的位置

    推导分两步:
        1. 在 X-Z 竖直平面内算位置(base_rotation=0,先不管左右转头)
        2. 绕 Z 轴旋转 θ0,得到最终 3D 坐标

    角度从 Z 轴量起(θ=0 时连杆竖直向上):
        竖直分量(z) → cos
        水平分量(x) → sin
    """
    # 度 → 弧度(sin/cos 要用弧度)
    θ0, θ1, θ2 = np.radians(joint_angles_deg[:3])

    # ==== 第 1 步: X-Z 平面内,3 段连杆逐段累加 ====

    # 肘部位置(上臂顶端)
    # 上臂从肩部(BASE_Z)出发,倾角 θ1
    elbow_x = L1 * np.sin(θ1)
    elbow_z = BASE_Z + L1 * np.cos(θ1)

    # 前臂顶端位置
    # 关键: elbow 角度是相对上臂的,末端总角度 = θ1 + θ2
    forearm_end_x = elbow_x + L2 * np.sin(θ1 + θ2)
    forearm_end_z = elbow_z + L2 * np.cos(θ1 + θ2)

    # 末端 site 位置(wrist=0,沿前臂方向再延伸 L3)
    site_x_planar = forearm_end_x + L3 * np.sin(θ1 + θ2)
    site_z = forearm_end_z + L3 * np.cos(θ1 + θ2)

    # ==== 第 2 步: 绕 Z 轴旋转(base_rotation) ====
    # 平面内末端只有 x 分量(前后),y=0
    # 绕 Z 转 θ0 后: x = r·cos(θ0), y = r·sin(θ0)
    x = site_x_planar * np.cos(θ0)
    y = site_x_planar * np.sin(θ0)

    return (x, y, site_z)


def get_mujoco_end_pos(model, data, joint_angles_deg):
    """用 Mujoco 拿 ground truth 末端位置。

    用 data.qpos 直接设关节角度(不是 ctrl),然后 mj_forward
    只更新几何位置,不跑物理 — 这样得到纯几何答案,没有 PD 稳态误差。
    """
    for i, ang in enumerate(joint_angles_deg):
        data.qpos[i] = np.radians(ang)
    mujoco.mj_forward(model, data)
    return tuple(data.site_xpos[0])


def main():
    model = mujoco.MjModel.from_xml_path("so101_arm.xml")
    data = mujoco.MjData(model)

    # 5 组测试角度 [base, shoulder, elbow, wrist]
    # 第 1 组全零,用于验证几何参数
    # 第 2 组是我们手算过的(预期 site 在 0.630, 0, 0.660 附近)
    test_cases = [
        [0,   0,   0,  0],   # 全归零: site 应在 (0, 0, 1.18)
        [0,  30,  60,  0],   # 手算过这组
        [0, -45,  90,  0],   # 伸手姿态
        [45, 30,  60,  0],   # 加 base 旋转
        [-30, -60, 30,  0],  # 复杂姿态
    ]

    print("=" * 60)
    print("FK 验证: 三角函数手算 vs Mujoco ground truth")
    print("误差 < 0.01m 为通过")
    print("=" * 60)

    all_pass = True
    for i, angles in enumerate(test_cases):
        fk_pos = compute_fk(angles)
        mj_pos = get_mujoco_end_pos(model, data, angles)

        error = np.linalg.norm(np.array(fk_pos) - np.array(mj_pos))
        passed = error < 0.01
        if not passed:
            all_pass = False

        print(f"\n[Test {i+1}] angles = {angles}")
        print(f"  FK:     ({fk_pos[0]:+.4f}, {fk_pos[1]:+.4f}, {fk_pos[2]:+.4f})")
        print(f"  Mujoco: ({mj_pos[0]:+.4f}, {mj_pos[1]:+.4f}, {mj_pos[2]:+.4f})")
        print(f"  Error:  {error:.4f}m  {'[PASS]' if passed else '[FAIL]'}")

    print("\n" + "=" * 60)
    if all_pass:
        print(">> 全部通过! FK 公式正确,误差均 < 0.01m")
    else:
        print(">> 有测试未通过 -- 检查公式/几何参数/关节轴方向")
    print("=" * 60)


if __name__ == "__main__":
    main()
