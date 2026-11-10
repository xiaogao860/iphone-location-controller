from PyInstaller.utils.hooks import collect_all

datas=[('iphone_location/assets','iphone_location/assets')]
binaries=[]
hiddenimports=[]
for package in ['pymobiledevice3','pmd_pytcp','pmd_net_addr','pmd_net_proto','developer_disk_image','pytun_pmd3']:
    d,b,h=collect_all(package)
    datas+=d;binaries+=b;hiddenimports+=h
# Keep the console subsystem so worker stdin/stdout remain available in frozen builds.
# The GUI launcher hides only its own newly allocated console window on Windows.
a=Analysis(['launcher.py'],pathex=['.'],binaries=binaries,datas=datas,hiddenimports=hiddenimports,
           hookspath=[],hooksconfig={},runtime_hooks=[],excludes=['IPython','matplotlib','tkinter'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='iPhoneLocationController',debug=False,
        bootloader_ignore_signals=False,strip=False,upx=False,console=True,disable_windowed_traceback=False)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='iPhoneLocationController')
