## macOS 原生版 1.4（附加发布）

新增 `iPhoneLocationController-macos-arm64.zip`：解压后运行「定位控制器.app」。架构为 Apple Silicon / arm64；原验证环境 macOS 26.6，依赖本机 `/usr/bin/python3`（Apple Python 3.9）及 Command Line Tools。第三方 Python 依赖已包含在应用内。本地临时签名，未做 Apple 公证。

此附件是原 Swift / AppKit / MapKit 原生版 1.4，保留 WASD、速度、路线、跑道和中国地图坐标校正；它与 Windows 2.0.0 的实现、版本号分别标注。应用包来自现有安装，签名检查通过、后端依赖导入通过、打包脚本与源码一致，Swift 源码重新编译检查通过。最终手机地图对齐仍需实机确认。

Mac 源码在 main 分支的 `macos/`，同时附上 `iPhoneLocationController-macos-source.zip` 和 `SHA256SUMS-macos.txt`。原 v2.0.0 标签仍指向已验证的 Windows 构建提交，自动生成的 Source code 下载不包含后加的 Mac 源码，请使用专用 Mac 源码附件。
