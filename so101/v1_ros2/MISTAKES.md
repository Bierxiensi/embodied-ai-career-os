# V1 ROS2 错题集（MISTAKES.md）

> 作用：记录真实踩过的坑，避免重复犯错。每一条都来自实际调试过程。

---

## 1. 误把 docker-desktop 当作 Linux 环境 → `sudo: not found`

**现象**：进入 WSL 后执行 `sudo apt update`，报 `-sh: sudo: not found`、`apt: not found`。

**原因**：`wsl` 命令默认进入的是带 `*` 的默认发行版，我的机器默认发行版是 **docker-desktop**。
docker-desktop 是一个**极简 Alpine 精简系统**（它的软件源用 `apk`，不是 `apt`），不是完整 Linux，
没有 `sudo`、`apt` 这些工具，**无法安装 ROS2**。

**教训**：
- `wsl -l -v` 里带 `*` 的那一行是"默认发行版"，`wsl` 直接进的就是它。
- 我的机器已有 Ubuntu-22.04，但默认不是它 → 需要显式指定 `wsl -d Ubuntu-22.04`。
- 判断系统类型：`cat /etc/os-release`（看 `ID=` 是不是 `ubuntu`，`VERSION_ID` 是不是 `22.04`）。
- 是否存在 `apt` 是判断"能否装 ROS2"的第一信号：`ls /usr/bin | grep apt`。

**正确做法**：
```bash
# 列出所有发行版，记住 Ubuntu-22.04 是否已装
wsl -l -v
# 退出当前(错误的)发行版
exit
# 显式进入 Ubuntu
wsl -d Ubuntu-22.04
```

---

## 2. Windows 盘符映射到 `/mnt/` → 代码在 WSL 里怎么访问 Windows 文件

**机制**：WSL2 会把 Windows 的盘符自动挂载到 Linux 的 `/mnt/<盘符>/` 下。

| Windows 路径 | WSL2 里的路径 |
|-------------|--------------|
| `D:\work\embodied-ai-career-os` | `/mnt/d/work/embodied-ai-career-os` |
| `C:\Users\zxy_2` | `/mnt/c/Users/zxy_2` |

**规律**：盘符大写字母 → `/mnt/` 后跟**小写盘符** + 反斜杠换成正斜杠。

**教训**：在 WSL 终端里操作 Windows 上的代码，要用 `/mnt/d/...` 而不是 `D:\...`：
```bash
cd /mnt/d/work/embodied-ai-career-os/so101/v1_ros2
```

**注意**：这样读的是同一个文件（Windows 和 WSL 共享同一磁盘），改代码两边都能看到。

---

## 3. `ModuleNotFoundError: No module named 'rclpy'` → 环境不对

**现象**：
```
File ".../simple_publisher.py", line 15, in <module>
    import rclpy
ModuleNotFoundError: No module named 'rclpy'
```

**原因（两个叠加）**：
1. **系统不对**：`rclpy` 只能装/运行在 Linux 上（Ubuntu 22.04 或 WSL2），Windows 原生环境没有它。
2. **没 source 环境**：即使在 WSL，ROS2 的 Python 库也不在默认 `sys.path` 里，
   必须先 `source /opt/ros/humble/setup.bash` 让 Python 能找到 `rclpy`。

**正确做法**：
```bash
# 每次新开终端都要 source（也可写入 ~/.bashrc 自动执行）
source /opt/ros/humble/setup.bash
# 验证是否可用
python3 -c "import rclpy; print('rclpy OK')"
```

**教训**：
- 先确认操作系统（`cat /etc/os-release`）再想装 ROS2。
- 报 `rclpy` 找不到，**先 source，而不是急着 pip install**。ROS2 用 apt/source 管理，不用 pip 装 rclpy。

---

## 4. 误用 `python -m 相对包路径` 启动 → ROS2 脚本要用 `python3 文件.py`

**现象**：
```bash
python -m so101.v1_ros2.reference.simple_publisher
# → ModuleNotFoundError: No module named 'rclpy'
```

**原因**：ROS2 的脚本是**"脚本式"**运行（`python3 脚本.py`），不是把 `so101` 当 Python 包用 `-m` 导入。
且参考目录在 `reference/`，应按 README 在脚本所在目录直接 `python3` 运行。

**正确做法**：在 `v1_ros2/` 目录下直接运行脚本文件：
```bash
cd /mnt/d/work/embodied-ai-career-os/so101/v1_ros2
python3 simple_publisher.py
```

---

## 5. `create_publisher` / `create_timer` "没看到定义" → 来自父类 Node（继承）

**疑问**：明明只写了 `self.create_publisher(...)`，没看到函数定义，怎么会生效？

**答案**：`SimplePublisher(Node)` 继承了 `rclpy.node.Node` 基类。这两个方法是 Node 在
**库内部已定义好的**，子类通过"继承"直接调用。真正驱动它们的是 `rclpy.spin(node)`。

**数据流**：
```
rclpy.spin(node)
   ├──> 定时器每 0.5s 触发 → timer_callback()        ← create_timer(0.5, 回调) 登记
   └──> timer_callback → publisher_.publish(msg)      ← create_publisher() 创建

create_publisher(String, "chatter", 10)   # = 在 topic "chatter" 上建发布器，缓冲 10
create_timer(0.5, self.timer_callback)     # = 每 0.5 秒调用一次回调
super().__init__("talker")                 # = 调用父类构造，给节点起名 "talker"
```

**教训**：遇到"方法没在文件里定义却能用"，先看类是否 **继承自 Node**；OOP 继承是 ROS2 一切节点的基础。

---

## 6. `rclpy.shutdown` 被调用两次 → `RCLError: rcl_shutdown already called`

**现象**：按 Ctrl+C 退出 `joint_subscriber.py` 时打印：
```
RCLError: failed to shutdown: rcl_shutdown already called on the given context
```

**原因**：在 ROS2 Humble，按 Ctrl+C 时 `rclpy.spin()` 内部**已经自动关闭 context**。
而 `finally` 里又手动调了 `rclpy.shutdown()` ×1 → 总共关闭了两次 → 第二次报"已关闭"。
**程序功能不受影响**（回调都正常执行了），只是收尾多关一次。

**修复**：shutdown 前用 `rclpy.ok()` 判断 context 是否还活着：
```python
finally:
    node.destroy_node()
    if rclpy.ok():          # 只有还活着才关闭，避免重复 shutdown
        rclpy.shutdown()
```

**教训**：
- `rclpy.spin()` 被 Ctrl+C 中断时可能已自行关闭 context，`finally` 里要防重复关闭。
- 报 `rcl_shutdown already called` = "关闭了两次"，不是功能 bug。
- 标准收尾模板：
  ```python
  rclpy.init()
  node = ...
  try:
      rclpy.spin(node)
  except KeyboardInterrupt:
      pass
  finally:
      node.destroy_node()
      if rclpy.ok():
          rclpy.shutdown()
  ```

---

## ✅ 成功示例（对照）

```bash
python3 simple_publisher.py
# [INFO] [talker]: Publishing: 'Hello ROS2: 0'
# [INFO] [talker]: Publishing: 'Hello ROS2: 1'
# ... 每 0.5 秒一条，Ctrl+C 停止
```