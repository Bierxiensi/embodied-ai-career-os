"""验证自建 SO101 3-DOF 机械臂模型能加载并渲染。"""
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

print("\n✅ SO101 arm model verified")
