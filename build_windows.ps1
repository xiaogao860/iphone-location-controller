$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw '请先安装 Python 3.11 x64。' }
}
& .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw '依赖安装失败' }
& .venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw '测试失败，停止构建' }
& .venv\Scripts\python.exe -m PyInstaller --noconfirm --clean iPhoneLocationController.spec
if ($LASTEXITCODE -ne 0) { throw '构建失败' }
Copy-Item README.md dist\iPhoneLocationController\README.md
Write-Host '完成：dist\iPhoneLocationController\iPhoneLocationController.exe'
