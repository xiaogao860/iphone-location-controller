# iPhone Location Controller — Windows

Windows 桌面版 iPhone 定位模拟控制器，使用 Python、PySide6 / Qt WebEngine 和 pymobiledevice3。由原 macOS Swift/AppKit 版本重构，定位后端与地图/运动计算分离。

## 功能

- USB 连接 iPhone，准备开发支持组件，使用用户态 RSD/DVT 连接。
- WASD 按住移动、松开停止、斜向速度归一化。失去窗口焦点停止手动移动。
- 速度单位 km/h，无人为上限，要求有限非负数；自动跑路线要求大于零。
- 地图点击选择起点或跑道中心。手绘路线的第一次点击就是首点，不插入其他位置。
- 路线自动移动、暂停/继续、终点停止、循环；自动路线在窗口失焦后继续。
- 一键生成两直道、两半圆组成的闭合跑道；可调整周长、朝向。
- 恢复真实定位；正常关闭应用前等待后端清除模拟定位。
- 固定点、WASD、路线全部使用相同 GPS/WGS-84 发送路径。高德/腾讯坐标可显式导入并转换一次。

## 下载 Windows 应用

在 GitHub 的 **Actions → Windows build → 成功运行 → Artifacts** 中下载 `iPhoneLocationController-windows-x64`，解压下载文件，再完整解压其中的应用 ZIP。双击 `iPhoneLocationController.exe`。

请保留整个应用文件夹，不能只拿出 EXE；Qt WebEngine 和 Python 依赖在旁边的 `_internal` 中。开发支持组件首次下载和地图瓦片加载需要网络。文件未签名、未作 Windows 商业发行签名。

构建产物只在工作流成功后出现。构建完成不代表 Windows + iPhone 真机测试已通过。

## Windows 环境

- Windows 10/11 x64。源码运行推荐 Python 3.11 x64；便携包无需另装 Python。
- Apple Mobile Device Service / USB 驱动。优先使用 Apple 官方提供的 iTunes Windows 安装程序；先确认电脑可识别手机。
- iPhone 解锁、信任电脑、开启开发者模式。目标连接是 iOS 17.4+，主要用于原项目的 iOS 26 设备；更老版本未支持。
- 一次只连接一部 iPhone。优先用 USB，不依赖 Wi-Fi 设备发现。

官方参考：[pymobiledevice3 Windows 故障排查](https://doronz88.github.io/pymobiledevice3/guides/troubleshooting/)、[iOS 开发连接说明](https://doronz88.github.io/pymobiledevice3/guides/ios17-tunnels/)、[Apple 官方 iTunes 下载](https://www.apple.com/itunes/download/win64)。

## 使用

1. 连接并解锁手机，完成信任和开发者模式。
2. 点击“连接手机”，等待就绪。单独连接不会修改定位。
3. 手动模式：选择起点或输入 GPS 坐标，点击“应用输入坐标”，再开始 WASD。输入框编辑时不会响应移动键。
4. 手绘模式：选择“绘制路线”，在地图依次点击，设置速度后“开始路线跑步”。路径按点间直线连接，不自动沿路规划。
5. 跑道：点击地图选择中心，设置周长和朝向，一键生成后开始路线跑步。默认周长 400 米；0° 长轴朝北，正角度顺时针。默认 -15° 可自行调整。
6. “循环路线”会从终点回到首点；手绘路线需自行闭合，避免最后跳回起点。
7. 用完点击“恢复真实定位 / 断开”，再在手机地图点击当前位置确认。

恢复指令发送成功不等于手机界面已经刷新。拔线、进程崩溃或强制终止可能使恢复失败，此时重新连接并恢复，必要时重启手机。应用不会自动关闭开发者模式。连接准备时关闭应用会等待开发连接完成后清理，最长可能需要约三分钟。

## 地图和坐标

Windows 版使用本地打包的 Leaflet 1.9.4，远程瓦片为 Esri World Imagery 与 OpenStreetMap。地图/路线/手机注入统一 WGS-84，不再沿用 macOS MapKit 中国底图的隐式坐标模式。瓦片服务是否可访问取决于网络；地图加载失败时可以输入坐标操作。

默认中心为北邮沙河校区操场附近 `40.1574011978, 116.2801353860`（WGS-84），由旧版地图点近似转换而来。**原对话尚未确认修正后手机上的最终对齐，此点不是实测测绘值，可自行微调。** GCJ-02→WGS-84 是本地近似算法，入口仅用于显式导入。不要对本应用地图点击结果再做转换。

地图服务会接收用于加载瓦片的区域信息；本项目不设置账号系统、分析服务或应用遥测。归属信息保留在地图上；本地第三方库许可见 `iphone_location/assets/LEAFLET-LICENSE`。

## 从源码启动 / 构建

双击 `start_windows.cmd`（首次需联网安装依赖），或在 PowerShell 中：

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe launcher.py
```

构建便携版：

```powershell
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean iPhoneLocationController.spec
```

也可在已允许脚本的 PowerShell 中运行 `./build_windows.ps1`，完成依赖安装、测试和构建。

## 验证与边界

- 单元测试覆盖速度、斜向移动、路线转向、终点、循环多圈、跨日期变更线、跑道长度与闭合、坐标导入。
- 后端测试用替代连接检查：固定点发送、EOF/错误/停止后清除模拟、显式坐标转换。
- 无手机 GUI 测试检查启动、路线绘制首点、跑道生成和控件状态。
- Windows GitHub Actions 执行测试、PyInstaller 打包和打包后依赖自检。
- 原 macOS 版本曾在 iOS 26.5.1 验证定位读取。本次 Windows 重构的 USB 连接、驱动和手机真实效果仍需 Windows 真机验证，不能由 CI 或 Mac 测试代替。
- 速度参数通过连续坐标推进实现，不保证手机提供的 speed/heading 元数据与设置一致。网络延迟、手机处理速度及地图精度会影响效果。
- 仅操作手机定位服务；不调用目标 App 的业务接口，不提交跑步、签到或成绩记录。

## 结构与许可

`iphone_location/app.py` Qt 界面与进程管理；`motion.py` 纯运动计算；`backend.py` 手机连接和恢复；`coordinates.py` 坐标导入；`assets/` 地图；`tests/` 自动检查。

本项目按 GPL-3.0 发布，与使用的 GPL-3.0 pymobiledevice3 保持一致。Leaflet 为 BSD-2-Clause；PySide6/Qt 及其第三方组件保留各自许可。仓库不包含 Apple 驱动、手机配对记录、开发镜像或旧版 Mac 二进制。

## macOS 原生版

Mac 版也已加入本仓库，见 [macos/README.md](macos/README.md)。它保留原 Swift / AppKit / MapKit 实现，版本 1.4，面向 Apple Silicon，依赖系统 Apple Python / Command Line Tools。现有 v2.0.0 Release 附加 Mac 应用 ZIP 与独立源码 ZIP；Windows 与 Mac 的版本号、地图实现和验证范围分别标明。
