import multiprocessing
import runpy
import sys

def main():
    multiprocessing.freeze_support()
    if len(sys.argv)>1 and sys.argv[1]=='--backend':
        from iphone_location.backend import main as backend
        return backend()
    if len(sys.argv)>1 and sys.argv[1]=='--pmd3':
        sys.argv=['pymobiledevice3',*sys.argv[2:]]
        runpy.run_module('pymobiledevice3',run_name='__main__')
        return 0
    if len(sys.argv)>1 and sys.argv[1]=='--self-test':
        from iphone_location.motion import Route, track, DEFAULT_CENTER
        from iphone_location.backend import child_command
        from pymobiledevice3.remote.userspace_tunnel import establish_userspace_rsd
        from PySide6.QtWebEngineWidgets import QWebEngineView
        assert Route(track(DEFAULT_CENTER)).total>399
        assert child_command('usbmux','list')
        import os,time
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS','--disable-gpu')
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QCoreApplication,QEvent
        from iphone_location.app import Window
        import shiboken6
        app=QApplication([]);window=Window();window.show()
        until=time.monotonic()+10
        while not window.map_ready and time.monotonic()<until:
            app.processEvents();time.sleep(.01)
        loaded=window.map_ready
        window.web.stop();window.close();shiboken6.delete(window)
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
        assert loaded,'Bundled Leaflet/WebChannel initialization failed'
        print('Bundled imports, motion, and map initialization self-test passed',flush=True)
        return 0
    if sys.platform=='win32':
        # Do not hide a terminal belonging to the user or a parent process.
        import ctypes
        ids=(ctypes.c_ulong*2)()
        if ctypes.windll.kernel32.GetConsoleProcessList(ids,2)==1:
            handle=ctypes.windll.kernel32.GetConsoleWindow()
            if handle:ctypes.windll.user32.ShowWindow(handle,0)
    from iphone_location.app import main as gui
    return gui()

if __name__=='__main__':
    raise SystemExit(main())
