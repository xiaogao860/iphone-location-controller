# macOS 原生版（1.4.1）

这是先前的 Swift / AppKit / MapKit 原生 Mac 版本，独立于仓库根目录的 Windows / Qt 版本。

## 下载与运行

在最新 Release（v2.1.0）中下载 `iPhoneLocationController-macos-arm64.zip`，解压后打开其中的「定位控制器.app」。这是 Mac 原生版 1.4.1 应用包，不是 Windows 2.x 的 Mac 移植，也不是 Intel/Universal 应用。

- 架构：Apple Silicon / arm64。
- 原验证环境：macOS 26.6 + iOS 26.5.1；其他版本未逐一测试。
- 使用本机 `/usr/bin/python3`，原包内扩展依赖按 Apple Python 3.9 构建，第三方依赖已在应用 Resources/python 内。需要已安装 Apple Command Line Tools，首次可用 `xcode-select --install` 安装。
- 应用为本地临时签名，未作 Apple 公证；无 Developer ID 商业发行签名。
- USB 连接手机、信任电脑、开启开发者模式，再点击连接。

WASD、速度参数、地图选点、手绘路线、一键生成跑道、暂停/继续、循环、恢复真实定位功能均保留。具体操作见本目录的《原版使用说明》。

Mac MapKit 中国底图与 Windows 的地图实现不同：Mac 版保留「中国地图坐标校正（GCJ-02 → GPS）」开关。此前已验证转换计算和发送，但最终手机地图对齐尚未收到确认。默认位置为天安门广场，可地图选点或输入坐标更改。

## 从源码构建

在安装了 Apple Command Line Tools 的 Apple Silicon Mac 上，从仓库根目录执行：

```sh
bash macos/build.sh
```

脚本用本机 `/usr/bin/python3` 创建独立环境并安装 `pymobiledevice3==11.27.2`，编译 Swift 界面、复制运行依赖并作临时签名；输出到 `dist/macos/定位控制器.app`。这不修改 /Applications 内已有应用，也不会自动连接手机或改变定位。依赖安装与首次开发支持组件准备需要网络。

`Sources/` 包含 Swift 界面、路线/跑道计算和 Python 定位后端。可分别编译检查界面、验证 Python 依赖；v2.1.0 起发布的应用包由 `macos/build.sh` 从当前源码构建。

## 发布说明

同一 v2.0.0 Release 包含 Windows 2.0.0 和附加的 macOS 原生 1.4。Mac 源码追加到 main 分支，原 v2.0.0 标签保持指向已验证的 Windows 构建提交；因此 Mac 版同时提供单独的源码 ZIP，不能仅依赖该标签自动生成的 Source code 下载。

许可：GPL-3.0，见仓库 LICENSE；第三方 Python 包保留各自许可。使用后点击恢复按钮，并在手机地图确认真实位置恢复。断线或强制终止时，可能需要重连恢复或重启手机。
