"""验证自建 SO101 3-DOF 机械臂模型能加载并渲染。

用法:
    python verify_model.py          # 无头验证（终端输出）
    python verify_model.py --view   # 打开交互式可视化窗口

在可视化窗口中:
    右键拖拽 = 旋转视角
    滚轮     = 缩放
    中键拖拽 = 平移
    Ctrl+滚轮 = 微调缩放
"""
import sys
from pathlib import Path

import mujoco

MODEL_PATH = Path(__file__).parent / "so101_arm.xml"

model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
data = mujoco.MjData(model)

print(f"Model loaded: {model.nbody} bodies, {model.njnt} joints, {model.nu} actuators")
print(f"Joints:    {[model.joint(i).name for i in range(model.njnt)]}")
print(f"Actuators: {[model.actuator(i).name for i in range(model.nu)]}")
print(f"Timestep:  {model.opt.timestep:.4f}s")

# 验证能渲染
with mujoco.Renderer(model, 480, 640) as renderer:
    mujoco.mj_forward(model, data)
    renderer.update_scene(data)
    pixels = renderer.render()
    print(f"Rendered: {pixels.shape}")

print("\n[OK] SO101 arm model verified")

# 交互式可视化
if "--view" in sys.argv:
    import mujoco.viewer
    print("\n启动交互式可视化窗口 (关闭窗口退出)...")
    print("鼠标操作: 右键旋转 | 滚轮缩放 | 中键平移")
    with mujoco.viewer.launch_passive(model, data) as viewer:
        while viewer.is_running():
            mujoco.mj_forward(model, data)
            viewer.sync()
