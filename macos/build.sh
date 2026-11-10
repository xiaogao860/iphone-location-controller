#!/bin/bash
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_dir"
if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
  echo 'This build targets Apple Silicon macOS.' >&2
  exit 1
fi
runtime_dir="$repo_dir/build/macos-runtime"
bundle_dir="$repo_dir/dist/macos/定位控制器.app"
/usr/bin/python3 -m venv "$runtime_dir"
"$runtime_dir/bin/python" -m pip install 'pymobiledevice3==11.27.2'
mkdir -p "$bundle_dir/Contents/MacOS" "$bundle_dir/Contents/Resources"
xcrun swiftc macos/Sources/main.swift macos/Sources/RouteMotion.swift macos/Sources/TrackGeometry.swift -o "$bundle_dir/Contents/MacOS/LocationController" -framework Cocoa -framework MapKit
cp macos/Info.plist "$bundle_dir/Contents/Info.plist"
cp macos/Sources/backend.py macos/Sources/coordinate_conversion.py "$bundle_dir/Contents/Resources/"
"$runtime_dir/bin/python" - "$bundle_dir" <<'PY'
from pathlib import Path
import shutil,sys,sysconfig
source=Path(sysconfig.get_paths()['purelib'])
dest=Path(sys.argv[1])/'Contents/Resources/python'
shutil.copytree(source,dest,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
PY
codesign --force --deep --sign - "$bundle_dir"
codesign --verify --deep --strict "$bundle_dir"
echo "Built: $bundle_dir"
