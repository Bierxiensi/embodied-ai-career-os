"""验证 Mujoco 安装 + 基础渲染。"""
import mujoco

# 用最小场景验证渲染管线
XML = """
<mujoco>
  <worldbody>
    <light pos="0 0 5"/>
    <body pos="0 0 0.5">
      <joint type="free"/>
      <geom type="box" size="0.1 0.1 0.1"/>
    </body>
  </worldbody>
</mujoco>
"""

model = mujoco.MjModel.from_xml_string(XML)
data = mujoco.MjData(model)

with mujoco.Renderer(model, 480, 480) as renderer:
    mujoco.mj_forward(model, data)
    renderer.update_scene(data)
    pixels = renderer.render()
    print(f"Rendered {pixels.shape}, Mujoco OK!")
